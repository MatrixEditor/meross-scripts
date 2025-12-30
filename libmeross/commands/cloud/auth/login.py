import argparse

from rich.console import Console
from pydantic import ValidationError

from libmeross.config import settings
from libmeross.protocol import CloudMessage, CloudResponse
from libmeross.util import logger, hash_password
from libmeross.commands.shared import (
    parser_add_host,
    parser_add_timeout,
    parser_add_user_agent,
    parser_add_extra_header,
    get_additional_headers,
    send_message,
    parser_get_usage,
)
from libmeross.model import ResultLogin, RequestLogin


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "login",
        help="Login to Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Meross Cloud API login tool",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_timeout(parser)
    parser_add_host(parser, settings.cloud.domain or "iot.meross.com")

    account_group = parser.add_argument_group("Account-Options")
    account_group.add_argument(
        "-U",
        "--username",
        type=str,
        help="The username to sign up with",
        default=settings.account.email or None,
    )
    account_group.add_argument(
        "-p",
        "--password",
        type=str,
        help="The password to sign up with",
        default=None,
    )
    account_group.add_argument(
        "--hash",
        type=str,
        help="The md5 hash of the password.",
        default=None,
    )
    account_group.add_argument(
        "--mfa-code",
        type=str,
        help="The MFA code to use",
        default="",
    )

    utility_group = parser.add_argument_group("Utility-Options")
    utility_group.add_argument(
        "--use-encryption",
        action="store_true",
        help="Use encryption for the password",
    )
    utility_group.add_argument(
        "--login-path",
        type=str,
        default="/v1/Auth/signIn",
        help="The path to the login endpoint (defaults to: '/v1/Auth/signIn')",
    )
    parser.set_defaults(func=cli)


def cli(argv: argparse.Namespace) -> None:
    console = Console()
    if settings.account.token:
        for row in (
            "Already logged in. If you want to login again, run `mrs cloud logout` first.",
            "Otherwise, the token within the configuration file will be overwritten.",
        ):
            logger.warning(row)

        choice = console.input(r"[bold yellow]Q : Continue? \[Y/n][/] ")
        if choice.lower() != "y":
            return

    host = argv.host
    url = f"https://{host}{argv.login_path}"
    logger.debug(f"Backend URL: {url}")

    if argv.username is None:
        logger.error("Username is required")
        return

    if argv.hash:
        argv.password = argv.hash
        argv.use_encryption = True

    if not argv.password:
        if not settings.account.password:
            logger.warn("Password not set but required is required")
            argv.password = console.input(
                "[bold yellow]> : Password: [/]", password=True
            )
        else:
            # password encrypted, but not enforced via CLI
            if not argv.use_encryption and settings.account.passwordEncrypted:
                for row in (
                    "Password is encrypted (MD5) in configuration file, ",
                    "but disabled via CLI. Password encryption will be applied.",
                ):
                    logger.warning(row)
                argv.use_encryption = True
                argv.password = settings.account.password
            elif settings.account.passwordEncrypted:
                argv.password = settings.account.password
            else:
                argv.password = hash_password(settings.account.password)

    else:
        if argv.use_encryption and not argv.hash:
            argv.password = hash_password(argv.password)

    payload = RequestLogin(
        email=argv.username,
        password=argv.password,
        encryption=1 if argv.use_encryption else 0,
        mfaCode=argv.mfa_code,
    )
    headers = get_additional_headers(argv)
    mesage = CloudMessage.new(payload)
    response = send_message(
        url, mesage, headers=headers, target=CloudResponse, timeout=argv.timeout
    )
    if not response:
        return

    if response.apiStatus != 0:
        logger.error(f"Login failed: {response}")
        return

    try:
        data = ResultLogin.model_validate(response.data)
    except ValidationError as e:
        logger.error(f"Failed to parse login response: {e}")
        return

    logger.info("Login successful:")
    logger.info("=" * 50)
    logger.info(f" - User-ID: {data.userid}")
    logger.info(f" - Username: {data.email}")
    logger.info(f" - Token: {data.token}")
    logger.info(f" - Key: {data.key}")
    logger.info("=" * 50)

    settings.account.token = data.token
    settings.account.key = data.key
    settings.account.email = data.email
    settings.account.userId = data.userid
    settings.cloud.domain = data.domain.removeprefix("https://")
    settings.cloud.mqttDomain = data.mqttDomain

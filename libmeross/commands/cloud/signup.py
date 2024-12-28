import argparse

from pydantic import BaseModel, ValidationError
from rich import console

from libmeross.config import settings
from libmeross.util import logger, hash_password
from libmeross.protocol import CloudMessage, CloudResponse
from libmeross.commands.shared import (
    get_additional_headers,
    parser_add_host,
    send_message,
    parser_add_user_agent,
    parser_add_extra_header,
    parser_add_timeout,
    parser_get_usage,
)

from .login import ResultLogin


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "signup",
        help="Sign up for Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Sign up tool for your Meross Cloud account",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_timeout(parser)
    parser_add_host(parser)

    account_group = parser.add_argument_group("Account-Options")
    account_group.add_argument(
        "-U",
        "--username",
        type=str,
        help="The username to sign up with (default is from config)",
        default=settings.account.email or None,
    )
    account_group.add_argument(
        "-p",
        "--password",
        type=str,
        help="The password to sign up with (default is from config)",
        default=None,
    )

    utility_group = parser.add_argument_group("Utility-Options")
    utility_group.add_argument(
        "--use-encryption",
        action="store_true",
        help="Use encryption for the password (MD5 - not really encrypted)",
    )
    utility_group.add_argument(
        "--signup-path",
        type=str,
        default="/v1/Auth/signUp",
        help="The path to the signup endpoint (defaults to: '/v1/Auth/signUp')",
    )

    parser.set_defaults(func=cli)


# --- model --
class SignUpData(BaseModel):
    username: str
    password: str
    encryption: int


def cli(argv: argparse.Namespace) -> None:
    if argv.signup_path[0] != "/":
        argv.signup_path = f"/{argv.signup_path}"

    url = f"https://{argv.host}{argv.signup_path}"
    logger.debug(f"Backend URL: {url}")
    if argv.username is None:
        logger.error("Username is required")
        return

    # REVISIT: duplicate code
    if not argv.password:
        if not settings.account.password:
            logger.warn("Password not set but required is required")
            input_console = console.Console()
            argv.password = input_console.input(
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
        if argv.use_encryption:
            argv.password = hash_password(argv.password)

    payload = SignUpData(
        username=argv.username,
        password=argv.password,
        encryption=1 if argv.use_encryption else 0,
    )

    headers = get_additional_headers(argv)
    message = CloudMessage.new(payload)
    response = send_message(
        url, message, headers=headers, target=CloudResponse, timeout=argv.timeout
    )
    if not response:
        return

    if response.apiStatus != 0:
        logger.error(f"Failed to sign up: {response}")
        return

    try:
        data = ResultLogin.model_validate(response.data)
    except ValidationError as e:
        logger.error(f"Failed to sign up: {e}")
        return

    logger.info("Registration successful:")
    logger.info("=" * 50)
    logger.info("User-Configuration:")
    logger.info(f" - User-ID: {data.userid}")
    logger.info(f" - Username: {data.email}")
    logger.info(" - Password: *****")
    logger.info(f" - User-Key: {data.key}")
    logger.info(f" - User-Token: {data.token}")
    logger.info("Cloud-Configuration:")
    logger.info(f" - Cloud-Domain: {data.domain}")
    logger.info(f" - MQTT-Domain: {data.mqttDomain}:443")
    logger.info("=" * 50)

    settings.account.token = data.token
    settings.account.userId = data.userid
    settings.account.email = data.email
    settings.account.key = data.key
    settings.account.password = argv.password
    settings.account.passwordEncrypted = argv.use_encryption
    settings.cloud.domain = data.domain.removeprefix("https://")
    settings.cloud.mqttDomain = data.mqttDomain

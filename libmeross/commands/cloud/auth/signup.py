import argparse
import logging
import uuid

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
        help="Sign up to Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Sign up tool for your Meross Cloud account",
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
    account_group.add_argument(
        "-V",
        "--vendor",
        type=str,
        help="The vendor to use within the registration data (default: meross)",
        default="meross",
    )
    account_group.add_argument(
        "--country",
        type=str,
        help="The country code to assign (default: cn)",
        default=settings.account.region or "cn",
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

    group = parser.add_argument_group("Additional Options")
    group.add_argument(
        "--mobile-resolution",
        type=str,
        default="2880*1440",
        help="Resolution of the mobile device",
    )
    group.add_argument(
        "--mobile-model",
        type=str,
        default="Pixel 3",
        help="Mobile device model",
    )
    group.add_argument(
        "--mobile-os",
        type=str,
        default="Android",
        help="Mobile device operating system)",
    )
    group.add_argument(
        "--mobile-os-version",
        type=str,
        default="16",
        help="Mobile device operating system version number",
    )
    group.add_argument(
        "--mobile-uuid",
        type=str,
        default=str(uuid.uuid4()),
        help="Mobile device uuid (always random)",
    )

    parser.set_defaults(func=cli)


# --- model --
class MobileInfo(BaseModel):
    resolution: str = "1*1"
    carrier: str = ""
    deviceModel: str = "Android,Android"
    mobileOs: str = "Android"
    mobileOsVersion: str = "16"
    uuid: str = str(uuid.uuid4())


class SignUpData(BaseModel):
    email: str
    password: str
    encryption: int
    vendor: str = "meross"
    accountCountryCode: str = "cn"
    mobileInfo: MobileInfo = MobileInfo()


def cli(argv: argparse.Namespace) -> None:
    if argv.signup_path[0] != "/":
        argv.signup_path = f"/{argv.signup_path}"

    if argv.host is None:
        return logger.error("No host specified!")

    url = f"https://{argv.host}{argv.signup_path}"
    logger.debug(f"Backend URL: {url}")
    if argv.username is None:
        logger.error("Username is required")
        return

    # REVISIT: duplicate code
    if not argv.password:
        if not settings.account.password:
            logger.warning("Password not set but required is required")
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
        email=argv.username,
        password=argv.password,
        encryption=1 if argv.use_encryption else 0,
        accountCountryCode=argv.country,
        vendor=argv.vendor,
        mobileInfo=MobileInfo(
            resolution=argv.mobile_resolution,
            mobileOs=argv.mobile_os,
            mobileOsVersion=argv.mobile_os_version,
            uuid=argv.mobile_uuid,
            deviceModel=f"Android,{argv.mobile_model}",
        ),
    )

    headers = get_additional_headers(argv)
    message = CloudMessage.new(payload)
    response = send_message(
        url, message, headers=headers, target=CloudResponse, timeout=argv.timeout
    )
    if not response:
        return

    if response.apiStatus != 0:
        return logger.error(f"Failed to sign up: {response}")

    try:
        data = ResultLogin.model_validate(response.data)
    except ValidationError as e:
        return logger.error(f"Failed to sign up: {e}")

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

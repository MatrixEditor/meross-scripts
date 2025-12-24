import argparse

from pydantic import ValidationError
from rich.console import Console, OverflowMethod
from rich.table import Table
from rich import print

from libmeross.protocol import CloudMessage, CloudResponse
from libmeross.util import logger
from libmeross.commands.shared import (
    get_additional_headers,
    send_message,
    parser_add_host,
    parser_add_timeout,
    parser_add_user_agent,
    parser_add_extra_header,
    require_info_level,
    parser_get_usage,
    parser_add_token
)
from libmeross.config import settings
from libmeross.model import UserInfoRequest, UserInfoResponse

def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "info",
        help="Get Account information from Meross Cloud",
        usage=parser_get_usage(__name__),
        description="User account information from the cloud",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_host(parser, settings.cloud.domain or "iot.meross.com")
    parser_add_timeout(parser)

    required_options = parser.add_argument_group("Required-Options")
    parser_add_token(required_options)
    parser.add_argument(
        "--tz",
        type=str,
        default="UTC",
        help="Timezone to use",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="cn",
        help="Region code to use",
    )
    parser.set_defaults(func=cli)

def cli(argv: argparse.Namespace) -> None:
    require_info_level(argv)
    logger.debug("Requesting firmwaccount information from Meross Cloud")
    url = f"https://{argv.host}/user/v1/baseInfo"
    logger.debug(f"Backend URL: {url}")

    if argv.token is None:
        logger.error("Token is required")
        return

    headers = get_additional_headers(argv)
    headers["Authorization"] = f"Bearer {argv.token}"
    request = UserInfoRequest(
        timezone=argv.tz,
        regionCode=argv.region,
    )

    message = CloudMessage.new(request)
    console = Console()
    with console.status("Fetching data..."):
        response = send_message(
            url, message, headers=headers, target=CloudResponse, timeout=argv.timeout
        )
        if not response:
            return

    try:
        account_data = UserInfoResponse.model_validate(response.data)
    except ValidationError as e:
        logger.error(f"Failed to validate response: {e}")
        return

    logger.info(f"Account '{account_data.nickname}' ({account_data.region})")
    logger.info(f"==> GUID: {account_data.guid}")
    logger.info(f"==> MFA: {account_data.mfaSwitch > 0}")
    if account_data.mobile:
        logger.info(f"==> Mobile: {account_data.mobile}")
    logger.info(f"==> Level: {account_data.level}")
    logger.info(f"==> GoldCoin: {account_data.goldCoin}")

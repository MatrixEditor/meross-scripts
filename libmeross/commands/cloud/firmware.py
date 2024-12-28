import argparse

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
from libmeross.model import Firmware, FirmwareUpdateConfig, RUpdateConfig


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "firmware",
        help="Get firmware from Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Firmware Update Lising based on registered devices",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_host(parser, settings.cloud.domain or "iot.meross.com")
    parser_add_timeout(parser)

    required_options = parser.add_argument_group("Required-Options")
    parser_add_token(required_options)
    parser.add_argument(
        "--fmware-path",
        type=str,
        default="/device/v1/fmware/upgradeVersion",
        help="The path to the firmware endpoint (defaults to: '/device/v1/fmware/upgradeVersion')",
    )
    parser.set_defaults(func=cli)


def cli(argv: argparse.Namespace) -> None:
    require_info_level(argv)
    logger.debug("Requesting firmware from Meross Cloud")

    url = f"https://{argv.host}{argv.fmware_path}"
    logger.debug(f"Backend URL: {url}")

    if argv.token is None:
        logger.error("Token is required")
        return

    headers = get_additional_headers(argv)
    headers["Authorization"] = f"Bearer {argv.token}"

    message = CloudMessage.new()
    console = Console()
    with console.status("Querying firmware..."):
        response = send_message(
            url, message, headers=headers, target=CloudResponse, timeout=argv.timeout
        )
        if not response:
            return

    if response.apiStatus != 0:
        logger.error(f"Failed to get firmware: {response}")
        return

    try:
        update_config = FirmwareUpdateConfig.model_validate(response.data)
    except ValidationError as e:
        logger.error(f"Failed to validate response: {e}")
        return

    firmwares = update_config.firmwares

    def list_firmwares(name: str, fware_list: list[RUpdateConfig]):
        table = Table(title=name)
        table.add_column("Device Uuid", justify="left", style="bold", overflow="fold")
        table.add_column("Type-SubType", justify="left", style="bold")
        table.add_column("Version", justify="left")
        table.add_column("Url", justify="left")
        table.add_column("MD5", justify="left")
        for fmware in firmwares.commonFirmwares:
            table.add_row(
                ", ".join(fmware.upgradeUuids),
                f"{fmware.type.upper()}-{fmware.subType.upper()}",
                fmware.version,
                str(fmware.url),
                fmware.md5,
            )
        print(table)

    if len(firmwares.commonFirmwares) == 0:
        logger.info("No common firmwares found")
    else:
        list_firmwares("Common Firmwares", firmwares.commonFirmwares)

    if len(firmwares.subFirmwares) == 0:
        logger.info("No sub firmwares found")
    else:
        list_firmwares("Sub Firmwares", firmwares.subFirmwares)

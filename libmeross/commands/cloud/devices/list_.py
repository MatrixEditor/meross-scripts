import argparse

from pydantic import ValidationError
from rich.table import Table
from rich import print
from rich.console import Console

from libmeross.model import OriginDevice
from libmeross.protocol import CloudMessage, CloudResponse
from libmeross.config import settings
from libmeross.util import logger
from libmeross.commands.shared import (
    get_additional_headers,
    send_message,
    parser_add_host,
    parser_add_extra_header,
    parser_add_timeout,
    parser_add_user_agent,
    require_info_level,
    parser_get_usage,
    parser_add_token
)



def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "list",
        help="List devices from Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Device listing tool for your Meross Cloud account",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_host(parser, settings.cloud.domain or "iot.meross.com")
    parser_add_timeout(parser)
    account_options = parser.add_argument_group("Account-Options")
    parser_add_token(account_options)
    utility_options = parser.add_argument_group("Utility-Options")
    utility_options.add_argument(
        "--devices-path",
        type=str,
        default="/v1/Device/devList",
        help="The path to the devices endpoint (defaults to: '/v1/Device/devList')",
    )
    parser.set_defaults(func=cli)


# --- model --
def cli(argv) -> None:
    require_info_level(argv)
    console = Console()

    url = f"https://{argv.host}{argv.devices_path}"
    logger.debug(f"Backend URL: {url}")

    if argv.token is None:
        logger.error("Token is required")
        return

    headers = get_additional_headers(argv)
    headers["Authorization"] = f"Bearer {argv.token}"

    message = CloudMessage.new()
    with console.status("Querying devices..."):
        response = send_message(
            url, message, headers=headers, target=CloudResponse, timeout=argv.timeout
        )
        if not response:
            return

    if response.apiStatus != 0:
        logger.error(f"Failed to list devices: {response}")
        return

    if len(response.data) == 0:
        logger.info("No devices found")
        return

    table = Table(title="Devices")
    table.add_column("UUID", justify="left", style="bold")
    table.add_column("Name", justify="left")
    table.add_column("Type", justify="left")
    table.add_column("Firmware/Hardware", justify="left")
    for device_raw in response.data:
        try:
            device = OriginDevice.model_validate(device_raw)
        except ValidationError as e:
            logger.error(f"Failed to validate device: {e}")
            continue

        table.add_row(
            device.uuid,
            device.devName,
            f"{device.deviceType.upper()}-{device.subType.upper()}",
            f"{device.fmwareVersion}/{device.hdwareVersion}",
        )
    print(table)

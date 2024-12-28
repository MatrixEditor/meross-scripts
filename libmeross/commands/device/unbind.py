import argparse
import requests

from rich.console import Console

from libmeross.config import settings
from libmeross.protocol import LocalMessage
from libmeross.commands.shared import (
    parser_add_host,
    parser_add_key,
    require_info_level,
    parser_get_usage,
    parser_add_timeout,
    confirm
)
from libmeross.util import logger


def install_parser(modules: argparse._SubParsersAction) -> None:
    parser = modules.add_parser(
        "unbind",
        help="Unbind the device from the local Wifi (Setup)",
        usage=parser_get_usage(__name__),
        description="Meross device unbinding tool",
    )
    parser_add_key(parser)
    parser_add_host(parser, settings.device.deviceIp)
    parser_add_timeout(parser)
    parser.set_defaults(func=cli)


def cli(argv) -> None:
    require_info_level(argv)

    url = f"http://{argv.host}/config"
    logger.debug(f"Sending messages to {url}")

    message = LocalMessage.new("PUSH", "Appliance.Control.Unbind", shared_key=argv.key)
    for row in (
        "The device will go into AP after the request has been sent.",
        "Please wait for a few seconds before attempting to connect again.",
    ):
        logger.info(row)

    console = Console()
    if not confirm(console, "Continue?"):
        return
    try:
        with console.status("Unbinding device..."):
            _ = requests.post(url, json=message.model_dump(), timeout=argv.timeout)
        # if we get a response, we used a wrong key
        logger.error("Failed to unbind the device - wrong shared key")
    except requests.exceptions.ConnectTimeout:
        logger.error("Failed to unbind the device - connection timed out")
    except requests.exceptions.RequestException:
        # ignore
        pass

import argparse

from pydantic import BaseModel

from libmeross.util import logger
from libmeross.config import settings
from libmeross.protocol import LocalMessage
from libmeross import mqtt
from libmeross.model import Firmware, Hardware, Online
from libmeross.commands.shared import (
    send_message,
    parser_add_host,
    parser_add_key,
    require_info_level,
    parser_get_usage,
)


# --- models --
class All(BaseModel):
    class System(BaseModel):
        firmware: Firmware
        hardware: Hardware
        online: Online

    system: System
    digest: dict


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "info",
        help="Get device info",
        usage=parser_get_usage(__name__),
        description="Device information gathering tool",
    )
    parser_add_key(parser)
    parser_add_host(parser, settings.device.deviceIp)
    parser.set_defaults(func=cli)


def cli(argv):
    require_info_level(argv)

    url = f"http://{argv.host}/config"
    logger.debug(f"Sending message to {url}")

    key = argv.key
    message = LocalMessage.new("GET", "Appliance.System.All", shared_key=key)
    dev_info = send_message(url, message, target=LocalMessage)
    if not dev_info:
        return

    if not dev_info.verify(key):
        logger.warning(
            "Message verification failed - the message could be tampered with"
        )

    info = All.model_validate(dev_info.payload["all"])
    hardware = info.system.hardware
    firmware = info.system.firmware
    mcid = mqtt.generate_device_client_id(hardware.uuid)
    musr = hardware.macAddress
    mpwd = mqtt.generate_password(firmware.userId, hardware.macAddress, key)

    logger.info("=" * 50)
    logger.info(
        f"{hardware.type.upper()}-{hardware.subType.upper()} "
        rf"\[{hardware.chipType}] ({firmware.compileTime})"
    )
    logger.info("=" * 50)
    logger.info("Device:")
    logger.info(f" - User-Id: {firmware.userId or '[red]<not set>[/red]'}")
    logger.info(rf" - Version: fw\[{firmware.version}] hw\[{hardware.version}]")
    logger.info(f" - UUID   :  {hardware.uuid}")
    logger.info(f" - MAC    :  {musr}")
    logger.info("MQTT:")
    logger.info(f" - Client-Id: {mcid}")
    logger.info(f" - Username : {musr}")
    logger.info(f" - Password : {mpwd}")
    logger.info("Cloud:")
    logger.info(f" - Server: {firmware.server}:{firmware.port}")

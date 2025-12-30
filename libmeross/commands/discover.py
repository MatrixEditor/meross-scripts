import argparse
import socket

from rich.console import Console
from pydantic import ValidationError

from libmeross.commands.shared import (
    parser_add_timeout,
    parser_get_usage,
)
from libmeross.util import logger
from libmeross.model import HIRequest, HIResponse

# Define constants
MRS_HI_BCAST = "255.255.255.255"
MRS_HI_SEND_PORT = 9988
MRS_HI_RECV_PORT = 9989
MRS_HI_DEFAULT_ID = "49f33d8a2de2f2089ccf45ba8cdd4440"


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "discover",
        aliases=["hi"],
        help="Tries to discover local Meross devices (all of them)",
        usage=parser_get_usage(__name__),
        description="Device discovery tool",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_timeout(parser)
    parser.set_defaults(func=cli)


def cli(argv: argparse.Namespace) -> None:
    logger.debug("Creating listening socket on port 9989")
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.settimeout(argv.timeout or 3)
    server.bind(("", MRS_HI_RECV_PORT))

    query = HIRequest(id=MRS_HI_DEFAULT_ID).model_dump_json()
    logger.debug("Sending payload to broadcast")
    logger.debug(f"Message OUT: {query}")
    _ = server.sendto(query.encode(), (MRS_HI_BCAST, MRS_HI_SEND_PORT))

    console = Console()
    status = console.status("Listening for devices...")
    devices: list[tuple[bytes, str]] = []
    try:
        status.start()
        while True:
            data, addr = server.recvfrom(1024)
            status.stop()
            logger.debug(f"New device found at {addr}")
            logger.debug(f"Message IN: {data.decode(errors='replace')}")

            devices.append((data, addr))
            status.start()
    except (socket.timeout, KeyboardInterrupt):
        pass
    finally:
        server.close()
        status.stop()

    logger.debug(f"Identified {len(devices)} devices!")
    for response, addr in devices:
        try:
            data = HIResponse.model_validate_json(response, extra="ignore")
        except ValidationError:
            logger.error(f"Invalid data received from device at {addr}")
            continue

        logger.info(f"({data.deviceType}-{data.subType}) Device '{data.devName}'")
        logger.info(f" Software: {data.devSoftWare}")
        logger.info(f" Hardware: {data.devHardWare}")
        logger.info(f" Location: {data.ip}:{data.port}")
        logger.info(f" UUID    : {data.uuid}\n")

    if len(devices) == 0:
        logger.warning("No devices identified")

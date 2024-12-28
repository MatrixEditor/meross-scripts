import argparse
import json

from rich import print

from libmeross.protocol import LocalMessage
from libmeross.util import logger
from libmeross.config import settings
from libmeross.commands.shared import (
    send_message,
    parser_add_host,
    parser_add_key,
    parser_get_usage,
)


def install_parser(modules: argparse._SubParsersAction) -> None:
    parser = modules.add_parser(
        "query",
        help="Execute commands or fetch information from the device",
        usage=parser_get_usage(__name__),
        description="Execute commands or fetch information from the device",
    )
    parser.add_argument(
        "namespace",
        type=str,
        help="The scene to execute",
    )
    parser.add_argument(
        "-X",
        "--method",
        type=str,
        help="The method to execute (default: GET)",
        default="GET",
    )
    parser.add_argument(
        "-P",
        "--payload",
        type=str,
        help="The payload to send. Use '@<filepath>' to load from a json file.",
        default=None,
    )
    parser.add_argument(
        "-I",
        "--headers",
        action="store_true",
        help="Print the headers of the response",
    )
    parser.add_argument(
        "-O",
        "--output",
        type=argparse.FileType("w"),
        help="The output file to save the response to",
        default=None,
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=2,
        help="The timeout of the request in seconds (default: 2)",
    )
    parser_add_key(parser)
    parser_add_host(parser, settings.device.deviceIp)
    parser.set_defaults(func=cli)


def cli(argv):
    url = f"http://{argv.host}/config"
    logger.debug(f"Sending messages to {url}")

    message = LocalMessage.new(argv.method, argv.namespace, shared_key=argv.key)
    if argv.payload is not None:
        try:
            if argv.payload.startswith("@"):
                argv.payload = argv.payload[1:]
                with open(argv.payload, "r") as f:
                    message.payload = json.load(f)
            else:
                message.payload = json.loads(argv.payload)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse payload: {e}")
            return
        except OSError as e:
            logger.error(f"Failed to open payload file: {e}")
            return

    response = send_message(url, message, timeout=argv.timeout)
    if not response:
        return

    data_json = (
        response.model_dump_json() if argv.headers else json.dumps(response.payload)
    )
    if argv.output:
        argv.output.write(data_json)
    else:
        print(data_json)

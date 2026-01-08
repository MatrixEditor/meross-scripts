# this script is based on https://github.com/libretiny-eu/ltchiptool/blob/master/ltchiptool/soc/ambz2/util/ambz2tool.py
import argparse

from rich.console import Console

from libmeross.commands.chip.amebaz2.util import (
    command,
    init_fallback_connection,
    open_serial,
    parser_add_serial,
)
from libmeross.util import logger


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "console", help="Open a serial console in fallback mode"
    )
    parser_add_serial(parser)
    parser.set_defaults(func=cli)


def cli(argv: argparse.Namespace) -> None:
    console = Console()
    ser = open_serial(argv)
    if ser is None:
        return

    if not init_fallback_connection(ser, console):
        return

    try:
        # duplicate code to enable
        while True:
            next_line = console.input("$[bold]8710c[/]> ")
            if next_line == "exit":
                break

            if command(ser, next_line, inline=print) is None:
                logger.error("Connection closed due to on-chip error")
                break
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()

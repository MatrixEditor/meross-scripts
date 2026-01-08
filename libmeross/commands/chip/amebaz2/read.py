import argparse
import sys

from rich.console import Console
from rich.progress import Progress

from libmeross.commands.chip.amebaz2.util import (
    command,
    init_fallback_connection,
    open_serial,
    parser_add_serial,
)
from libmeross.util import logger
from libmeross.commands.shared import hexint, parser_get_usage


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "read",
        help="Read bytes from chip memory",
        usage=parser_get_usage(__name__),
        description="Chip Tool - Memory Read",
    )
    parser_add_serial(parser)
    parser.add_argument(
        "address",
        type=hexint,
        help="The address to read from",
    )
    parser.add_argument(
        "length",
        type=hexint,
        help="The number of bytes to read",
        default=16,
    )
    parser.add_argument(
        "--assume-download",
        action="store_true",
        help="Assume the device is in download mode",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("wb"),
        help="The output file to save the response to",
        default=sys.stdout.buffer,
    )
    parser.set_defaults(func=cli)


def cli(argv: argparse.Namespace) -> None:
    console = Console()
    if argv.verbose and argv.output is sys.stdout.buffer:
        logger.error("Verbose mode cannot be used with stdout output. ")
        return

    ser = open_serial(argv)
    if not ser:
        return

    if not argv.assume_download and not init_fallback_connection(ser, console):
        return

    progress = Progress() if argv.verbose else None
    if progress:
        progress.start()
        task = progress.add_task("Reading...", total=argv.length)

    text = f"DB {argv.address:#x} {argv.length}"
    end = min(argv.length, 16) + 4
    logger.debug(f"Working command: {text!r}")

    def write_line(line: str) -> None:
        line = line.strip()
        if line.startswith("[Addr]"):  # header
            return

        try:
            values = line[10:-end].strip().replace(" ", "")
            argv.output.write(bytes.fromhex(values))
            argv.output.flush()
            if progress:
                progress.update(task, advance=len(values) // 2)
        except Exception as e:
            logger.error(f"Failed to write line: {e}")
            logger.error(f"Line: {line}")
            return

    if command(ser, text, inline=write_line) is None:
        logger.error("Connection closed due to on-chip error")

    if progress:
        progress.stop()

    argv.output.close()
    ser.close()

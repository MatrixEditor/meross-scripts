# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false
import argparse
import lzma
from pathlib import Path

from rich.console import Console

from caterpillar.py import unpack

from libmeross.util import logger
from libmeross.commands.shared import parser_get_usage, require_info_level
from libmeross.mtk.image import fota_bin_info_t, fota_bin_t, fota_header_info_t


def install_parser(subparsers) -> None:
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "parse",
        help="Parse Over-the-Air (OTA) images from Mediatek chips",
        usage=parser_get_usage(__name__),
        description="Chip Tool - Firmware Image Parser",
    )
    parser.add_argument(
        "file",
        type=argparse.FileType("rb"),
        help="Path to the firmware binary",
    )
    parser.add_argument(
        "--split", type=Path, help="Directory to save all partitions to"
    )
    parser.set_defaults(func=cli)


def cli(argv: argparse.Namespace):
    require_info_level(argv)
    console = Console()
    logger.debug(f"Parsing OTA inage at {argv.file.name}")
    try:
        header = unpack(fota_header_info_t, argv.file)
    except Exception as e:
        logger.error(f"Could not parse image: {e}")
    else:
        print(f"Partition count: {header.bin_num}")
        for bin_num in range(header.bin_num):
            # structure is relatively simple:
            #   - text: bytes[bin_length] at bin_offset
            #   - signature: bytes[20]
            bin_info: fota_bin_info_t = header.bin_info[bin_num]
            console.print(
                f" - [{bin_num}] {bin_info.bin_start_addr:#08x}: {bin_info.bin_length}b ",
                highlight=False,
                end="",
            )

            try:
                argv.file.seek(bin_info.bin_offset)
                bin_part = unpack(fota_bin_t, argv.file, length=bin_info.bin_length)
                if bin_info.is_compressed:
                    bin_data = lzma.decompress(bin_part.bin_data)
                else:
                    bin_data: bytes = bin_part.bin_data
            except Exception as e:
                console.print("[red]Fail[/]")
                logger.error(f"Failed to parse partition {bin_num}: {e}")
                continue

            console.print(
                f"[green]Ok[/] ({len(bin_data)} actual bytes)", highlight=False
            )
            if argv.split:
                argv.split.mkdir(exist_ok=True, parents=True)
                path: Path = argv.split / f"{bin_num}.bin"
                logger.debug(f"({bin_num}) Saving contents to {path}")
                path.write_bytes(bin_data)

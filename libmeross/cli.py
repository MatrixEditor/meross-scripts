__doc__ = """\
Small utilities to control and interact with Meross (smart) devices

Environment options:
  MEROSS_CONFIG\tThe path to the configuration file (default
               \tpoints to ~/.config/meross/config.json)
"""
import argparse

from .util import logger, setup_logging
from .commands import CMD_LIST
from .config import settings, save_config


def cli_entry():
    parser = argparse.ArgumentParser(
        description=__doc__,
        usage="mrs [GLOBAL OPTIONS] [COMMAND] ...",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    global_options = parser.add_argument_group("Global Options")
    global_options.add_argument(
        "-d", "--debug", action="store_true", help="Enables debug log messages"
    )
    global_options.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enables verbose log messages (INFO level)",
    )
    modules = parser.add_subparsers(title="Commands")

    for install_hook in CMD_LIST:
        if install_hook:
            install_hook(modules)

    argv = parser.parse_args()
    if not hasattr(argv, "func"):
        parser.print_help()
        return

    if argv.debug:
        setup_logging("DEBUG")
    elif argv.verbose:
        setup_logging("INFO")
    else:
        setup_logging("WARNING")

    logger.debug(f"Running command {argv.func.__module__}")
    try:
        argv.func(argv)
    except KeyboardInterrupt:
        logger.log(12, "Interrupted by user")
    finally:
        if settings.persistConfig:
            logger.debug("Saving configuration...")
            save_config()

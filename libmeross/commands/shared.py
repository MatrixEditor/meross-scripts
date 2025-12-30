import requests
import typing
import argparse

from pydantic import BaseModel, ValidationError
from rich.console import Console
from libmeross.util import logger, setup_logging
from libmeross.config import settings
from libmeross.protocol import CloudResponse

_MT = typing.TypeVar("_MT", bound=BaseModel)
_RT = typing.TypeVar("_RT", bound=BaseModel)


def send_message(
    url: str,
    message: _MT,
    timeout: int = 2,
    headers: dict | None = None,
    target: type[_RT] | None = None,
) -> _MT | _RT | None:
    if url is None:
        logger.error(f"URL is None, skipping message: {message}")
        return None

    if message is None:
        logger.error(f"Message is None, skipping message: {message}")
        return None

    if not isinstance(message, BaseModel):
        logger.error(
            f"Message is not an instance of a BaseModel, skipping message: {type(message)}"
        )
        return None

    message_cls = target or message.__class__
    logger.debug(f"Message OUT: {message}")

    try:
        response = requests.post(
            url,
            json=message.model_dump(by_alias=True),
            timeout=timeout,
            headers=headers,
        )
        logger.debug(f"Message IN: {response.text}")
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
        logger.error(
            "Connection timed out: Make sure the device is active and "
            f"accessible at: {url!r}."
        )
        return
    except requests.exceptions.ConnectionError:
        if target is CloudResponse:
            rows = (
                "Could not connect to the specified cloud endpoint: ",
                f" - {url!r} ",
                "Make sure you have an internet connection and the URL is correct.",
            )
        else:
            rows = (
                "Connection closed by host: This is probably because the device ",
                "does not support the given method on the given namespace. Another ",
                "issue could be an invalid payload. Enable --debug to see what the ",
                "request looks like.",
            )
        for row in rows:
            logger.error(row)
        return None

    if response.status_code != 200:
        logger.error(
            f"Request failed with status code: {response.status_code}. "
            f"Response: {response.text}"
        )
        return None

    try:
        return message_cls.model_validate_json(response.text)
    except ValidationError as e:
        logger.error(f"Failed to parse response: {e}")
        return None


def parser_add_host(parser: argparse.ArgumentParser, default: str | None = None):
    parser.add_argument(
        "--host",
        type=str,
        help="The target host to connect to (default will be taken from config)",
        default=default,
    )


def parser_add_key(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-K",
        "--key",
        type=str,
        help="The shared key of the device",
        default=settings.account.key,
    )


def parser_add_extra_header(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-H",
        "--header",
        action="append",
        default=[],
        type=str,
        help="Add a custom header to the request (can be specified multiple times)",
    )


def parser_add_timeout(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-t", "--timeout", type=int, default=2, help="The timeout in seconds"
    )


def parser_add_user_agent(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-A",
        "--user-agent",
        type=str,
        help="The user agent to use",
        default="Mozilla/5.0 (Linux; Android) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.3",
    )


def parser_add_token(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-T",
        "--token",
        type=str,
        help="The token to use (default is from config)",
        default=settings.account.token or None,
    )


def get_additional_headers(argv) -> dict[str, str]:
    headers = {
        "Vendor": settings.app.vendor,
        "AppType": settings.app.appType,
    }
    for item in getattr(argv, "header", []):
        name, value = item.split(":", 1)
        headers[name] = value

    agent = getattr(argv, "user_agent", None)
    if agent:
        headers["User-Agent"] = agent

    return headers


def submodule(module) -> typing.Callable[[argparse._SubParsersAction], None]:
    def wrapper(subparsers: argparse._SubParsersAction) -> None:
        name = module.__name__.split(".")[-1]
        parser = subparsers.add_parser(
            name,
            help=module.__doc__,
            formatter_class=argparse.RawTextHelpFormatter,
            usage=parser_get_usage(module.__name__),
        )
        parser_modules = parser.add_subparsers(title="Commands")

        for mod in module.__dict__.values():
            install_hook = getattr(mod, "install_parser", None)
            if install_hook:
                install_hook(parser_modules)
            else:
                if getattr(mod, "__submodule__", False):
                    submodule(mod)(parser_modules)

    return wrapper


def require_info_level(argv):
    if not argv.verbose and not argv.debug:
        setup_logging("INFO")


def hexint(s: str) -> int:
    try:
        return int(s, 10)
    except ValueError:
        return int(s, 16)


def parser_get_usage(mod_name: str) -> str:
    parts = mod_name.replace("_", "").split(".")[2:]
    return f"mrs [GLOBAL OPTIONS] {' '.join(parts)} [OPTIONS]..."


def confirm(console: Console, prompt: str) -> bool:
    return console.input(r"[bold blue]Q : {} \[Y/n][/] ".format(prompt)).lower() == "y"

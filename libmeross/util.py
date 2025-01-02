import hashlib
import random
import string
import datetime
import logging

from rich.logging import RichHandler

logger = logging.getLogger("rich")


def generate_random(
    length: int, characters: str = string.ascii_lowercase + string.digits
) -> str:
    return "".join(random.choice(characters) for _ in range(length))


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def get_timestamp() -> int:
    return int(datetime.datetime.now().timestamp())


class _ColoredFormatter(logging.Formatter):
    FORMAT = {
        "DEBUG": "dim",
        "INFO": "blue",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold red",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.FORMAT.get(record.levelname, "magenta")
        prefix = f"[{color}]{record.levelname[0]} :"
        return f"{prefix} {record.getMessage()}[/]"


def setup_logging(level: str) -> None:
    handler = RichHandler(
        show_time=False, show_path=False, show_level=False, markup=True
    )
    handler.formatter = _ColoredFormatter()
    handler.highlighter = None  # pyright: ignore[reportAttributeAccessIssue]
    logger.setLevel(level)
    logging.basicConfig(handlers=[handler])

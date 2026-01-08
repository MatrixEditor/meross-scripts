import argparse

import serial

from serial.tools.list_ports import comports
from typing import Callable
from rich.console import Console

from libmeross.util import logger

CMD_START_FALLBACK_MODE = b"Rtk8710C"
CMD_PROMPT = b"$8710c>"
CMD_RESULT_SUCCESS = [b"Command NOT found.", CMD_PROMPT]
CMD_NEWLINE = b"\n"
CMD_BUS_FAULT = b"S-Domain Fault"


def init_fallback_connection(ser: serial.Serial, console: Console):
    # try to enter fallback mode
    ser.write(CMD_START_FALLBACK_MODE + CMD_NEWLINE)
    try:
        data = ser.read_until(CMD_PROMPT)
        if CMD_PROMPT not in data:
            logger.error(f"Failed to enter fallback mode - invalid response: {data}")
            return False

        return True
    except TimeoutError:
        logger.error("Failed to enter fallback mode")
    return False


def command(
    ser: serial.Serial,
    command: str,
    inline: Callable[[str], None] | None = None,
) -> str | None:
    ser.write(command.encode() + CMD_NEWLINE)
    first = True
    is_err = False
    text = []
    try:
        while line := ser.readline():
            if first:
                first = False
                continue

            cleaned = line.rstrip()
            if cleaned.startswith(CMD_PROMPT):
                return "\n".join(text)

            if cleaned.startswith(CMD_BUS_FAULT):
                is_err = True
                logger.error(cleaned.decode())
                continue

            if is_err:
                logger.error(cleaned.decode())
            else:
                if inline:
                    inline(cleaned.decode())
                else:
                    text.append(cleaned.decode())
    except TimeoutError:
        print("Connection closed due to on-chip error")
        pass

    return None if is_err else "\n".join(text)


def parser_add_serial(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--port",
        type=str,
        help="The serial port to use",
        default=None,
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        help="The baudrate to use (default: 115200)",
        default=115200,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="The timeout to use (default: 1.0)",
        default=0.2,
    )


def open_serial(argv) -> serial.Serial | None:
    if argv.port is None:
        logger.warn("No serial port specified - searching available ports")
        try:
            devices = comports()
        except serial.SerialException:
            logger.error("Failed to list serial ports")
            return

        if len(devices) == 0:
            logger.error("No serial ports found")
            return

        for device in devices:
            logger.info(f" | {device.device_path}")

        logger.info("Using default serial port")
        argv.port = devices[0].device_path

    logger.debug(f"Opening serial port {argv.port} at {argv.baudrate} baud")
    try:
        ser = serial.Serial(argv.port, argv.baudrate, timeout=argv.timeout)
        if ser.is_open:
            logger.debug("Serial port opened")
            return ser
    except serial.SerialException:
        pass
    logger.error(f"Failed to open serial port at {argv.port}")

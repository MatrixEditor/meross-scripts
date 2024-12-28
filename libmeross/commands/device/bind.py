import argparse
import base64

from pydantic import BaseModel
from rich.console import Console

from libmeross.protocol import LocalMessage
from libmeross.util import logger, setup_logging
from libmeross.commands.shared import (
    send_message,
    parser_add_host,
    parser_add_key,
    parser_get_usage,
)
from libmeross.config import settings
from libmeross.model import WifiList


def install_parser(modules: argparse._SubParsersAction) -> None:
    parser: argparse.ArgumentParser = modules.add_parser(
        "bind",
        help="Bind the device to the local Wifi (Setup)",
        usage=parser_get_usage(__name__),
        description="Meross device binding tool",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    mqtt_group = parser.add_argument_group("MQTT-Options")
    mqtt_group.add_argument(
        "--mqtt-host",
        type=str,
        default=[],
        action="append",
        help="The hostname or IP address (<host>:<port>) of the MQTT broker.",
    )
    mqtt_group.add_argument(
        "-U",
        "--user-id",
        type=str,
        help=(
            "The user id to configure alongside with MQTT (will be "
            "taken from config if not set)"
        ),
        default=settings.account.userId or None,
    )

    wifi_group = parser.add_argument_group("Wifi-Options")
    wifi_group.add_argument(
        "--wifi-ssid",
        type=str,
        help="The SSID of the network to connect to",
        default=settings.device.wifiSsid or None,
    )
    wifi_group.add_argument(
        "--wifi-pass",
        type=str,
        help="The password of the network to connect to",
        default=settings.device.wifiPass or None,
    )
    parser_add_key(parser)
    parser_add_host(parser, settings.device.deviceIp)
    parser.set_defaults(func=cli)


# --- model --
class Gateway(BaseModel):
    host: str
    port: str
    redirect: int = 1
    secondHost: str = ""
    secondPort: str = "0"


class Config(BaseModel):
    key: str
    userId: str
    gateway: Gateway


def cli(argv):
    if not argv.debug and not argv.verbose:
        setup_logging("INFO")

    url = f"http://{argv.host}/config"
    logger.debug(f"Working with {url}")
    console = Console()

    if len(argv.mqtt_host) > 0:
        for row in (
            "MQTT Configuration:",
            "-" * 69,
            "Check if your MQTT broker is running and accepts connections over ",
            "tls. The device will go into AP mode if the broker or network cannot ",
            "be found.",
        ):
            logger.info(row)

        servers = [s.split(":") for s in argv.mqtt_host]
        gateway = Gateway(
            host=servers[0][0],
            port=servers[0][1],
            secondHost=servers[1][0] if len(servers) > 1 else servers[0][0],
            secondPort=servers[1][1] if len(servers) > 1 else servers[0][1],
        )
        logger.info("Gateway:")
        logger.info(f" - Primary Host: {gateway.host}:{gateway.port}")
        if len(servers) > 1:
            logger.info(f" - Secondary Host: {gateway.secondHost}:{gateway.secondPort}")

        if not argv.key:
            for row in (
                "No key provided - the device won't be able to login to the ",
                "official MQTT broker.",
            ):
                logger.warning(row)

        config = Config(
            key=argv.key,
            userId=argv.user_id,
            gateway=gateway,
        )
        payload = {"key": config.model_dump()}
        message = LocalMessage.new("SET", "Appliance.Config.Key", payload)
        response = send_message(url, message)
        # REVISIT: maybe verification?
        if response is not None:
            logger.info("MQTT configuration successful")
            settings.account.userId = argv.user_id
            settings.account.key = argv.key
        else:
            return

    if argv.wifi_ssid and argv.wifi_pass:
        for row in (
            "Wifi Configuration:",
            "-" * 68,
            "The given Wifi network should be using a 2.4Ghz channel that is ",
            "different from the device's channel. Note that the credentials will ",
            "be transmitted base64 encoded within a HTTP request. Be sure to ",
            "change the password before setting up the device.",
        ):
            logger.info(row)

        logger.debug("Querying nearby wifi networks...")
        with console.status("Querying nearby wifi networks (max 10s)..."):
            networks_response = send_message(
                url,
                LocalMessage.new("GET", "Appliance.Config.WifiList"),
                timeout=10,
            )
            if not networks_response:
                return

        networks = WifiList.model_validate(networks_response.payload)
        wifi_spec = None
        for wifi in networks.wifiList:
            if wifi.ssid == argv.wifi_ssid:
                wifi_spec = wifi
                logger.debug(f"Found SSID: {wifi_spec.ssid}")
                break

        if wifi_spec is None:
            logger.error(f"Could not find SSID: {argv.wifi_ssid}")
            return

        message = LocalMessage.new("SET", "Appliance.Config.Wifi")
        message.payload = {"wifi": wifi_spec.model_dump()}
        message.payload["wifi"]["password"] = base64.b64encode(
            argv.wifi_pass.encode()
        ).decode()
        response = send_message(url, message)
        if response is not None:
            logger.info("Wifi configuration complete!")

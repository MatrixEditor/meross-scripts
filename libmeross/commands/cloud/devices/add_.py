import argparse
import ssl

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from pydantic_extra_types.mac_address import MacAddress

from libmeross.commands import device
from libmeross.commands.shared import (
    get_additional_headers,
    parser_add_extra_header,
    parser_add_host,
    parser_add_key,
    parser_add_timeout,
    parser_add_user_agent,
    send_message,
    require_info_level,
    parser_add_token,
    parser_get_usage,
)
from libmeross.config import settings
from libmeross.protocol import CloudMessage, CloudResponse, LocalMessage
from libmeross.util import logger
from libmeross.mqtt import generate_device_client_id, generate_password
from libmeross.model import BindRequest, OriginDevice, Time, Firmware, Hardware


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "add",
        help="Add a device to Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Device binding tool (Cloud)",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_key(parser)
    parser_add_host(parser, settings.cloud.domain or "iot.meross.com")
    parser_add_timeout(parser)

    device_options = parser.add_argument_group("Device-Options")
    device_options.add_argument(
        "-M",
        "--mac",
        type=str,
        help="The MAC address of the device (either from config or from device)",
        default=settings.device.mac or None,
    )
    device_options.add_argument(
        "--uuid",
        type=str,
        help="The UUID of the device (either from config or from device)",
        default=settings.device.uuid or None,
    )
    parser_add_token(parser)
    parser.add_argument(
        "--mqtt-domain",
        type=str,
        help="The MQTT domain to use",
        default=settings.cloud.mqttDomain or "mqtt.meross.com",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="The user id to configure alongside with MQTT",
        default=settings.account.userId or None,
    )
    device_options.add_argument(
        "-D",
        "--device-ip",
        type=str,
        help="The IP address of the device to bind",
        default=settings.device.deviceIp,
    )
    parser.add_argument(
        "--no-privacy",
        action="store_true",
        help="Disable privacy mode",
    )

    parser.set_defaults(func=cli)


def _send_local_message(url, path, target, key, item):
    message = LocalMessage.new("GET", path, shared_key=key)
    response = send_message(url, message)
    if not response:
        return None

    if not response.verify(key):
        logger.warn("Could not verify local response - message could be tampered with")

    try:
        return target.model_validate(response.payload[item])
    except ValidationError as e:
        logger.error(f"Failed to validate response: {e}")
        return None


def cli(argv):
    require_info_level(argv)

    if not argv.device_ip:
        logger.error("Missing device IP")
        return

    device_url = f"http://{argv.device_ip}/config"
    firmware = _send_local_message(
        device_url, "Appliance.System.Firmware", Firmware, argv.key, "firmware"
    )
    if not firmware:
        return

    if not argv.user_id:
        logger.warning("Missing user ID - falling back to device userId")
        settings.account.userId = argv.user_id = str(firmware.userId)

    hardware = _send_local_message(
        device_url, "Appliance.System.Hardware", Hardware, argv.key, "hardware"
    )
    if not hardware:
        return

    if not argv.uuid:
        logger.warning("Missing UUID - falling back to device UUID")
        settings.device.uuid = argv.uuid = str(hardware.uuid)

    if not argv.mac:
        logger.warning("Missing MAC - falling back to device MAC")
        settings.device.mac = argv.mac = str(hardware.macAddress)

    logger.info("=" * 50)
    logger.info(
        f"{hardware.type.upper()}-{hardware.subType.upper()} "
        rf"\[{hardware.chipType}] ({firmware.compileTime})"
    )
    logger.info("=" * 50)
    if not argv.no_privacy:
        logger.debug("Privacy mode is enabled - device details will be modified")
        firmware.innerIp = "10.10.10.1"  # fake IP for MQTT
        firmware.server = argv.mqtt_domain  # fake server for MQTT
        firmware.port = 443  # fake port for MQTT
        firmware.wifiMac = MacAddress("00:00:00:00:00:00")  # fake MAC for MQTT

    logger.info("MQTT Configuration")
    logger.info("-" * 50)
    client = mqtt.Client(
        client_id=generate_device_client_id(argv.uuid),
        protocol=mqtt.MQTTv5,
    )
    logger.info(f" - Client-Id: {client._client_id}")
    logger.info(f" - Username: {argv.mac}")
    logger.info("-" * 50)
    client.username_pw_set(
        argv.mac, generate_password(argv.user_id, argv.mac, argv.key)
    )
    client.tls_set(
        tls_version=ssl.PROTOCOL_TLSv1_2,
        cert_reqs=ssl.CERT_NONE,
        ca_certs=None,
    )
    client.tls_insecure_set(True)

    publish_topic = f"/appliance/{argv.uuid}/publish"
    subscribe_topic = f"/appliance/{argv.uuid}/subscribe"

    def on_connect(client: mqtt.Client, userdata, flags, rc, p):
        logger.debug(f"Connected with result code {rc}")
        if rc != 0:
            logger.error("Failed to connect to MQTT broker")
            client.disconnect()
            return

        logger.debug(f"Subscribing to {subscribe_topic}")
        client.subscribe(subscribe_topic)

        # publish bind message
        logger.info("Publishing bind message...")
        message = LocalMessage.new(
            "PUSH", "Appliance.Control.Bind", shared_key=argv.key
        )
        bind_request = BindRequest(
            bindTime=message.header.timestamp,
            time=Time(timestamp=message.header.timestamp),
            hardware=hardware,
            firmware=firmware,
        )

        message.payload = {"bind": bind_request.model_dump()}
        message.header.from_ = publish_topic
        logger.debug(f"Publishing message: {message}")
        client.publish(
            publish_topic,
            message.model_dump_json().encode(),
        )

        logger.info("Binding device to account using Cloud API...")
        api_bind_request = CloudMessage.new({"uuid": argv.uuid})
        headers = get_additional_headers(argv)
        headers["Authorization"] = f"Bearer {argv.token}"
        response = send_message(
            f"https://{argv.host}/v1/Device/devInfo",
            api_bind_request,
            target=CloudResponse,
            headers=headers,
            timeout=argv.timeout,
        )
        if response:
            if response.apiStatus != 0:
                logger.error(f"Failed to bind device: {response}")
            else:
                try:
                    origin_device = OriginDevice.model_validate(response.data)
                except ValidationError as e:
                    logger.error(f"Failed to validate response: {e}")
                    return

                logger.info("Successfully bound device to account:")
                logger.info(
                    f" - {origin_device.deviceType.upper()}-{origin_device.subType.upper()} "
                    rf"\[{origin_device.devName}]"
                )
        client.disconnect()

    def on_message(client: mqtt.Client, userdata, msg):
        logger.debug(f"Message received: {msg.topic} {msg.payload}")
        client.disconnect()

    client.on_connect = on_connect
    client.on_message = on_message

    logger.info(f"Connecting to MQTT broker at {argv.mqtt_domain}")
    client.connect(argv.mqtt_domain, 443, 60)
    client.loop_forever()

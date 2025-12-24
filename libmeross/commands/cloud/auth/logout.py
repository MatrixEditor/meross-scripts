import argparse

from libmeross.protocol import CloudMessage, CloudResponse
from libmeross.util import logger
from libmeross.config import settings
from libmeross.commands.shared import (
    get_additional_headers,
    send_message,
    parser_add_host,
    parser_add_timeout,
    parser_add_user_agent,
    parser_add_extra_header,
    parser_get_usage,
    parser_add_token,
)


def install_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "logout",
        help="Logout from Meross Cloud",
        usage=parser_get_usage(__name__),
        description="Logout tool for your Meross Cloud account",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser_add_user_agent(parser)
    parser_add_extra_header(parser)
    parser_add_host(parser, "iot.meross.com")
    parser_add_timeout(parser)

    required_group = parser.add_argument_group("Required-Options")
    parser_add_token(required_group)
    parser.add_argument(
        "--logout-path",
        type=str,
        default="/v1/Profile/logout",
        help="The path to the logout endpoint (defaults to: '/v1/Profile/logout')",
    )
    parser.set_defaults(func=cli)


def cli(argv):
    url = f"https://{argv.host}{argv.logout_path}"
    logger.debug(f"Backend URL: {url}")

    if argv.token is None:
        logger.error("Token is required")
        return

    headers = get_additional_headers(argv)
    headers["Authorization"] = f"Bearer {argv.token}"

    message = CloudMessage.new()
    response = send_message(
        url, message, headers=headers, target=CloudResponse, timeout=argv.timeout
    )
    if not response:
        return

    if response.apiStatus != 0:
        logger.error(f"Logout failed: {response}")
        return

    # clear token in configuration
    settings.account.token = ""
    logger.info("Logout successful")

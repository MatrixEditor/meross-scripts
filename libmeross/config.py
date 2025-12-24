import pathlib
import os

from pydantic import BaseModel

from libmeross.util import logger


class AppConfig(BaseModel):
    vendor: str = "meross"
    appType: str = "Android"


class AccountConfig(BaseModel):
    email: str = ""
    password: str = ""
    token: str = ""
    userId: str = ""
    key: str = ""
    passwordEncrypted: bool = False
    region: str = "cn"


class DeviceConfig(BaseModel):
    deviceIp: str = "10.10.10.1"
    wifiSsid: str = ""
    wifiPass: str = ""
    uuid: str = ""
    mac: str = ""


class CloudConfig(BaseModel):
    domain: str = ""
    mqttDomain: str = ""


class Config(BaseModel):
    account: AccountConfig = AccountConfig()
    app: AppConfig = AppConfig()
    device: DeviceConfig = DeviceConfig()
    cloud: CloudConfig = CloudConfig()
    persistConfig: bool = False


CONFIG_DEFAULT_DIR_PATH = pathlib.Path.home() / ".config" / "meross"
CONFIG_DEFAULT_FILE_PATH = CONFIG_DEFAULT_DIR_PATH / "config.json"
CONFIG_FILE_PATH = pathlib.Path(
    os.environ.get("MEROSS_CONFIG", str(CONFIG_DEFAULT_FILE_PATH))
)


def save_config(config_path: pathlib.Path | None = None) -> None:
    global settings
    config_path = config_path or CONFIG_FILE_PATH
    if config_path.is_dir():
        logger.error(f"Failed to save config: {config_path} is a directory")
        return
    try:
        if not config_path.parent.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)

        config_path.write_text(settings.model_dump_json(indent=2))
    except OSError as e:
        logger.error(f"Failed to save config: {e}")


settings = Config()
# TODO: add environment configuration

if CONFIG_FILE_PATH.exists() and not CONFIG_FILE_PATH.is_dir():
    try:
        settings = Config.model_validate_json(CONFIG_FILE_PATH.read_text())
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

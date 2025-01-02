from pydantic import BaseModel, PositiveInt, Base64Str
from pydantic_core import Url
from pydantic_extra_types.mac_address import MacAddress


class Firmware(BaseModel):
    version: str
    compileTime: str
    wifiMac: str
    innerIp: str
    server: str
    port: int
    userId: int


class Hardware(BaseModel):
    type: str
    subType: str
    version: str
    chipType: str
    uuid: str
    macAddress: MacAddress


class Online(BaseModel):
    status: int
    bindId: str = ""
    id: str = ""
    lastActiveTime: str = ""
    who: int = 0


class Wifi(BaseModel):
    ssid: Base64Str
    bssid: str
    channel: PositiveInt
    signal: int
    encryption: int
    cipher: int


class WifiList(BaseModel):
    wifiList: list[Wifi]


class Time(BaseModel):
    timestamp: int
    timezone: str = ""
    timeRule: list = []


class BindRequest(BaseModel):
    bindTime: int
    time: Time
    hardware: Hardware
    firmware: Firmware


# --- CLOUD MODELS ---
class ResultLogin(BaseModel):
    email: str
    key: str
    token: str
    userid: str
    mqttDomain: str
    domain: str


class RequestLogin(BaseModel):
    email: str
    password: str
    encryption: int
    agree: int = 1
    mfaCode: str = ""
    # optional
    # mobileInfo: dict = {}
    # accountCountryCode: str = ...


class OriginDevice(BaseModel):
    uuid: str
    devName: str
    devIconId: str
    bindTime: int
    deviceType: str
    subType: str
    region: str
    fmwareVersion: str
    hdwareVersion: str
    userDevIcon: str
    iconType: int
    domain: str
    reservedDomain: str
    hardwareCapabilities: list
    channels: list
    onlineStatus: int = 1


class RUpdateConfig(BaseModel):
    type: str
    subType: str
    version: str
    url: Url
    md5: str
    description: str
    mcu: list
    upgradeType: str
    upgradeUuids: list[str]


class FirmwareUpdateConfig(BaseModel):
    class DeviceTypeByUUID(BaseModel):
        uuid: str
        type: str
        subType: str

    class FirmwareConfig(BaseModel):
        commonFirmwares: list[RUpdateConfig]
        subFirmwares: list[RUpdateConfig]

    firmwares: FirmwareConfig
    deviceTypes: list[DeviceTypeByUUID] = []

from pydantic import BaseModel, PositiveInt, Base64Str
from pydantic_core import Url
from pydantic_extra_types.mac_address import MacAddress

# --- LOCAL MODELS ---
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
    timezone: str = "UTC"
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


class UserInfoResponse(BaseModel):
    avatar: str = ""
    birthday: str = ""
    dealSite: str = ""
    follower: int = -1
    following: int = -1
    forumSite: str = ""
    goldCoin: int = -1
    guid: str = ""
    guidGrayId: str = ""
    isBindAlexa: int = -1
    isBindGoogle: int = -1
    isBindSmartThings: int = -1
    level: int = -1
    mfaSwitch: int = -1
    mobile: str = ""
    nickname: str = ""
    posts: int = -1
    region: str = ""

class UserInfoRequest(BaseModel):
    timezone: str
    regionCode: str


# --- DISCOVERY MODELS ---
class HIRequest(BaseModel):
    id: str
    devName: str = "*"

class HIResponse(BaseModel):
    devName: str
    devSoftWare: str
    devHardWare: str
    ip: str
    port: int
    mac: str
    uuid: str
    deviceType: str
    subType: str
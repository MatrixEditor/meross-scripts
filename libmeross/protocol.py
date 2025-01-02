import json
import base64
import string
import uuid

from pydantic import Base64Str, BaseModel, PositiveInt, Field
from typing import Any, TypeVar

from libmeross import util

_MT = TypeVar("_MT", bound="BaseModel")


class Header(BaseModel):
    messageId: str
    timestamp: PositiveInt
    # timestampMs: PositiveInt
    sign: str
    method: str
    namespace: str
    # protocolVersion: PositiveInt = 1
    # payloadVersion: PositiveInt = 2
    # triggerSrc: str = ""
    # uuid: str = ""
    from_: str = Field(serialization_alias="from", default="Cloud")


class LocalMessage(BaseModel):
    header: Header
    payload: dict[str, Any]

    @staticmethod
    def signature(
        mid: str, timestamp: int | None = None, shared_key: str | None = None
    ) -> tuple[str, int]:
        if timestamp is None:
            timestamp = util.get_timestamp()
        sign = util.hash_password(f"{mid}{shared_key or ''}{timestamp}")
        return sign, timestamp

    @classmethod
    def new(
        cls,
        method: str,
        namespace: str,
        payload: BaseModel | dict | None = None,
        shared_key: str | None = None,
    ) -> "LocalMessage":
        message_id = util.generate_random(32, string.digits + "abcdef")
        sign, timestamp = cls.signature(message_id, shared_key=shared_key)

        if isinstance(payload, BaseModel):
            payload = payload.model_dump()

        return cls(
            header=Header(
                messageId=message_id,
                timestamp=timestamp,
                sign=sign,
                method=method,
                namespace=namespace,
            ),
            payload=payload or {},
        )

    def verify(self, shared_key: str | None = None) -> bool:
        sign, _ = LocalMessage.signature(
            self.header.messageId, self.header.timestamp, shared_key=shared_key
        )
        return sign == self.header.sign

    def get_payload(self, model: type[_MT], item: str | None = None) -> _MT:
        data = self.payload if not item else self.payload[item]
        return model(**data)

    def set_payload(self, model: BaseModel | dict, item: str | None = None):
        data = model.model_dump() if isinstance(model, BaseModel) else model
        if item:
            self.payload[item] = data
        else:
            self.payload = data


class CloudMessage(BaseModel):
    timestamp: PositiveInt
    nonce: str
    sign: str
    params: Base64Str

    @staticmethod
    def signature(
        data: str, timestamp: int | None = None, nonce: str | None = None
    ) -> tuple[str, str, int]:
        nonce = nonce or util.generate_random(16)
        timestamp = timestamp or util.get_timestamp()
        _secret = "23x17ahWarFH6w29"
        return (
            util.hash_password(f"{_secret}{timestamp}{nonce}{data}"),
            nonce,
            timestamp,
        )

    @classmethod
    def new(cls, data: dict | BaseModel | None = None) -> "CloudMessage":
        if isinstance(data, BaseModel):
            data_json = data.model_dump_json()
        else:
            data_json = json.dumps(data or {})

        data_base64 = base64.b64encode(data_json.encode()).decode()
        sign, nonce, timestamp = cls.signature(data_base64)
        return cls(
            timestamp=timestamp,
            nonce=nonce,
            sign=sign,
            params=data_base64,
        )

    def verify(self) -> bool:
        return (
            self.sign
            == CloudMessage.signature(self.params, self.timestamp, self.nonce)[0]
        )

    def get_payload(self, model: type[_MT] | None = None) -> dict | _MT:
        obj = json.loads(self.params)
        return model(**obj) if isinstance(model, type) else obj

    def set_payload(self, model: BaseModel | dict):
        data = model.model_dump() if isinstance(model, BaseModel) else model
        self.params = json.dumps(data)
        self.sign, *_ = CloudMessage.signature(self.params, self.timestamp, self.nonce)


class CloudResponse(BaseModel):
    apiStatus: int
    sysStatus: int
    info: str = ""
    timestamp: PositiveInt
    data: dict | list

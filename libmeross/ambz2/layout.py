# type: ignore
# Struct definitions and types taken from
# - https://github.com/Ameba-AIoT/ameba-rtos-z2/blob/main/doc/AN0500_Realtek_Ameba-ZII_Application_Note.pdf
# - https://github.com/libretiny-eu/ltchiptool
# - and elf2bin.exe from build SDK of AmebaZ2
#
#   Section 5.2 - Layout
#   ┌──────────────────┐
#   │ Partition Table  │ 0x00000020 - 0x00001000
#   ├──────────────────┤
#   │ System Data      │ 0x00001000 - 0x00002000
#   ├──────────────────┤
#   │ Calibration Data │ 0x00002000 - 0x00003000
#   ├──────────────────┤
#   │ Reserved         │ 0x00003000 - 0x00004000
#   ├──────────────────┤
#   │                  │
#   │ Boot Image       │ 0x00003000 - 0x0000C000
#   │                  │
#   ├──────────────────┤
#   │                  │
#   │                  │
#   │ Firmware 1       │ 0x0000C000
#   │                  │
#   │                  │
#   ├──────────────────┤
#   │                  │
#   │                  │
#   │ Firmware 2       │
#   │                  │
#   │                  │
#   ├──────────────────┤
#   │                  │
#   │ User Data        │
#   │                  │
#   └──────────────────┘
#
# NOTE: The actual addresses will be mapped to 0x98000000 - so the start address
# of 0 will be 0x98000000.
from enum import IntEnum
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.hashes import SHA256
from caterpillar.py import (
    S_DISCARD_UNNAMED,
    S_REPLACE_TYPES,
    Bytes,
    boolean,
    pack,
    padding,
    sizeof,
    struct,
    set_struct_flags,
    LittleEndian,
    this,
    uint16,
    uint32,
    uint8,
    Transformer,
    unpack,
)


set_struct_flags(S_DISCARD_UNNAMED, S_REPLACE_TYPES)

# --- Flash Memory Layout ---
# Section 5.2
Addr_FlashBase = 0x98000000
# defined in ROM
CALIBRATION_PATTERN = bytes.fromhex("999996963FCC66FCC033CC03E5DC3162")

Addr_FlashCalibrationPattern = Addr_FlashBase + 0x00000000
Len_FlashCalibrationPattern = 0x20

Addr_FlashPartitionTable = Addr_FlashBase + 0x00000020
Len_FlashPartitionTable = 0x1000 - 0x20  # 4K bytes

Addr_FlashSystemData = Addr_FlashBase + 0x00001000
Len_FlashSystemData = 0x1000  # 4K bytes

Addr_FlashCalibrationData = Addr_FlashBase + 0x00002000
Len_FlashCalibrationData = 0x1000  # 4K bytes

Addr_FlashReserved = Addr_FlashBase + 0x00003000
Len_FlashReserved = 0x1000  # 4K bytes

Addr_FlashBootImage = Addr_FlashBase + 0x00003000
Len_FlashBootImage = 0x8000  # 32K bytes

Addr_FlashFirmwareStart = Addr_FlashBase + 0x0000C000
# length not included here, but default firmware length is 0xF8000
Len_DefaultFirmware = 0xF8000

# --- Memory Layout ---
# Section 6.2 in RTL8720Cx-VH2_Datasheet_V1.0_20230224-1.pdf
Addr_ROM = 0x00000000
Len_ROM = 0x60000  # 384K bytes

Addr_SRAM = 0x10000000
Len_SRAM = 0x40000  # 256K bytes

Addr_BTSRAM = 0x20000000
Len_BTSRAM = 0x8000  # 32K bytes

# --- Partition Table Models ---
# Section 5.2.1
FF_32 = b"\xff" * 32
FF_12 = b"\xff" * 12


class ImageType(IntEnum):
    __struct__ = uint8

    # Image types according to _convert_img_type
    PARTAB = 0
    BOOT = 1
    FWHS_S = 2
    FWHS_NS = 3
    FWLS = 4
    ISP = 5
    VOE = 6
    WLN = 7
    XIP = 8
    WOWLN = 10
    CINIT = 11
    CPFW = 9
    UNKNOWN = 0x3F


@struct(order=LittleEndian)
class Header:
    # According to _create_img_header
    segment_size: uint32
    next_: uint32 = 0xFFFFFFFF
    type: ImageType
    encrypted: boolean
    is_special: boolean
    flags: uint8 = 0x00  # user keys not defined
    _: padding[8]
    serial: uint32
    _1: padding[8]
    user_key1: Bytes(32) = FF_32
    user_key2: Bytes(32) = FF_32


# According to Secion 5.2.1.1 the unspecified partition table header
# takes 96 bytes. Out struct should do the same
assert sizeof(Header) == 0x60


class PartitionType(IntEnum):
    __struct__ = uint8

    # Defined in _convert_pt_type
    PARTAB = 0
    BOOT = 1
    SYS = 2
    CAL = 3
    USER = 4
    FW1 = 5
    FW2 = 6
    VAR = 7
    MP = 8
    RDP = 9
    UNKNOWN = 10


# Partition Table record based on the information in section 5.2.1.1
@struct(order=LittleEndian)
class PartitionTableRecord:
    start: uint32
    length: uint32
    type: PartitionType
    dbg_skip: boolean = False
    _: padding[6]
    hkey_valid: boolean = False
    _1: padding[15]
    hash_key: Bytes(32) = FF_32


class FixedSize(Transformer):
    def __init__(self, length, s) -> None:
        super().__init__(Bytes(length))
        self.s = s

    def decode(self, parsed: bytes, context):
        return unpack(self.s, parsed)

    def encode(self, obj, context):
        data = pack(obj, self.s)
        target = self.__size__(context)
        return data + b"\x00" * (target - len(data))


# Even though the document specifies some regions within the partition
# table info as "reserved". However, these reserved regions are used
# within the generation process.
#
# The partition_table_cfg from JSON contains the following fields:
# Off   Len Type    Name
# 0x0	0x4	int		num
# 0x4	0x4	int		rma_w_state
# 0x8	0x4	int		rma_ov_state
# 0xc	0x4	int		eFWV
# 0x10	0x4	int		fw1_idx
# 0x14	0x4	int		fw2_idx
# 0x18	0x4	int		ota_trap
# 0x1c	0x4	int		mp_trap
# 0x20	0x4	int		key_exp_op
# 0x24	0x4	int		user_len
# 0x28	0x4	char *	user_ext
# 0x2c	0x4	char *	user_bin
# 0x30	0x4	int	    item_num
# 0x34	0x4	PARTITEMCFG *	items
@struct(order=LittleEndian)
class PartitionTableInfo:
    rma_w_state: uint8 = 0xFF
    rma_ov_state: uint8 = 0xFF
    eFWV: uint8
    _: padding[1]  # really reserved
    num: uint8
    fw1_idx: uint8
    fw2_idx: uint8
    _1: padding[3]  # reserved
    ota_trap: uint16 = 0x00
    mp_trap: uint16 = 0x00
    _2: padding[1]
    key_exp_op: uint8 = 0x00
    user_len: uint32
    user_ext: Bytes(0xC) = FF_12

    # Up to this point the partition table stores 0x40 bytes
    # key material, 0x60 bytes image header information and
    # 0x20 bytes partition table information. The remaining
    # bytes will be used to calculate the segment size within
    # the image header.
    # -----------------------------------------
    boot_record: PartitionTableRecord
    records: PartitionTableRecord[this.num]
    user_data: Bytes(this.user_len)


# The default user key to be used when creating the partition table
# can be found in the _manipulate_bootloader function or the ROM
# code.
HASH_KEY = bytes.fromhex(
    "47E5661335A4C5E0A94D69F3C737D54F2383791332939753EF24279608F6D72B"
)


# The function _manipulate_bootloader implements how the partition
# table is placed within the flash. (exluding the calibration pattern)
@struct(order=LittleEndian)
class PartitionTable:
    dec_pubkey: Bytes(32) = FF_32
    hash_pubkey: Bytes(32) = FF_32
    hdr: Header
    info: PartitionTableInfo
    hash: Bytes(32) = FF_32

    def build_hash(self, user_key: bytes) -> None:
        # As Section 5.2.1.1 states:
        #  Hash: from the first byte of partition table to the end of user data
        #  (two public keys + Header + partition info + partition records + user data),
        #  calculated before encryption if the encryption is on
        hmac_obj = HMAC(user_key, SHA256())
        data = pack(self)[:-32]
        hmac_obj.update(data)
        self.hash = hmac_obj.finalize()

    def set_segment_size(self) -> None:
        # the segment size is the size of all dynamic fields within the
        # partition table info
        size = len(pack(self.info))  # minus static fields is done in bootloader
        self.hdr.segment_size = size

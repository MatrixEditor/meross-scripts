# pyright: reportInvalidTypeForm=false, reportGeneralTypeIssues=false
# pyright: reportInvalidTypeArguments=false
# Struct definitions mostly adopted from here:
# - driver/board/mt25x3_hdk/bootloader/core/inc/bl_fota.h
# - middleware/MTK/fota/src/fota.c
from caterpillar.shortcuts import G
from caterpillar.py import (
    Bytes,
    DigestField,
    Sha1_Algo,
    padding,
    struct,
    uint32,
    uint8,
)
from caterpillar.byteorder import LittleEndian


# define FOTA_HEADER_MAGIC_PATTERN      0x004D4D4D  // "MMM"
FOTA_HEADER_MAGIC_PATTERN: bytes = b"MMM"
# define FOTA_HEADER_MAGIC_END_MARK          0x45454545
FOTA_HEADER_MAGIC_END_MARK: bytes = b"EEEE"
# define FOTA_BIN_NUMBER_MAX                     4
FOTA_BIN_NUMBER_MAX: int = 4
# define FOTA_SIGNATURE_SIZE                 (20)
FOTA_SIGNATURE_SIZE: int = 20

# define HAL_SHA1_DIGEST_SIZE     (20)  /**<  160 bits = 20  bytes */
HAL_SHA1_DIGEST_SIZE: int = 20

FOTA_SHA1 = DigestField("signature", Bytes(HAL_SHA1_DIGEST_SIZE), verify=True)


@struct(order=LittleEndian)
class fota_bin_t:
    _hash_begin: DigestField.begin("signature", Sha1_Algo)
    bin_data: Bytes(G.length)
    signature: FOTA_SHA1

@struct(order=LittleEndian)
class fota_bin_info_t:
    bin_offset: uint32
    bin_start_addr: uint32
    bin_length: uint32
    partition_length: uint32
    sig_offset: uint32
    sig_length: uint32
    is_compressed: uint32
    reserved: padding[4] = None


@struct(order=LittleEndian)
class fota_header_info_t:
    _hash_begin: DigestField.begin("signature", Sha1_Algo)
    magic: FOTA_HEADER_MAGIC_PATTERN
    ver: uint8
    bin_num: uint32
    bin_info: fota_bin_info_t[FOTA_BIN_NUMBER_MAX]
    signature: FOTA_SHA1

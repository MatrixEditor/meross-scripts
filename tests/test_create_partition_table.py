from caterpillar.py import pack
from rich import print

from libmeross.ambz2.layout import (
    CALIBRATION_PATTERN,
    FF_12,
    HASH_KEY,
    PartitionTable,
    PartitionTableInfo,
    PartitionType,
    PartitionTableRecord,
    Header,
    ImageType,
    FF_32,
    HMAC,
    SHA256,
)


def test_build_boot_record() -> PartitionTableRecord:
    boot_record: PartitionTableRecord = PartitionTableRecord(
        start=0x4000,
        length=0xC000,
        type=PartitionType.BOOT,
    )
    assert boot_record.hash_key == FF_32

    return boot_record


def test_build_firmware_records() -> list[PartitionTableRecord]:
    fw1_record: PartitionTableRecord = PartitionTableRecord(
        start=0x10000,
        length=0x000B0780,
        type=PartitionType.FW1,  # unused partition
    )
    fw2_record: PartitionTableRecord = PartitionTableRecord(
        start=0x110000,
        length=0x9c800,
        type=PartitionType.FW2,
    )
    return [fw1_record, fw2_record]


def test_build_pt_header() -> Header:
    pt_header: Header = Header(
        segment_size=0x3A0,  # will be set later on
        type=ImageType.PARTAB,
        encrypted=False,
        is_special=True,
        serial=0,
    )
    assert pt_header.user_key1 == FF_32
    assert pt_header.user_key2 == FF_32
    return pt_header


def test_build_pt_info() -> PartitionTableInfo:
    pt_info: PartitionTableInfo = PartitionTableInfo(
        eFWV=0x00,
        num=2,  # number excluding boot entry
        fw1_idx=1,
        fw2_idx=2,
        user_len=0x00,
        boot_record=test_build_boot_record(),
        records=test_build_firmware_records(),
        user_data=b"",
    )
    assert pt_info.user_ext == FF_12
    return pt_info


def test_build_pt() -> PartitionTable:
    pt: PartitionTable = PartitionTable(
        hdr=test_build_pt_header(),
        info=test_build_pt_info(),
    )
    assert pt.dec_pubkey == FF_32
    assert pt.hash_pubkey == FF_32
    assert pt.hash == FF_32

    pt.set_segment_size()
    pt.build_hash(HASH_KEY)
    return pt


def test_check_pt_hash() -> None:
    pt = test_build_pt()
    pt_data = pack(pt)

    hmac = HMAC(HASH_KEY, SHA256())
    index = (pt.hdr.segment_size + 0x5F & ~0x1F) + 0x20 + 0x40
    assert index == len(pt_data) - 32
    hmac.update(pt_data[:index])

    assert hmac.finalize() == pt.hash


if __name__ == "__main__":
    import argparse
    from libmeross.util import logger, setup_logging

    setup_logging("INFO")
    parser = argparse.ArgumentParser()
    parser.add_argument("flash", type=argparse.FileType("rb"))
    parser.add_argument("target", type=argparse.FileType("wb"))

    argv = parser.parse_args()

    pt = test_build_pt()
    pt_data = pack(pt)

    hmac = HMAC(HASH_KEY, SHA256())
    # Index := segment_size + 96 - 32
    # (32 is the static fields size)
    index = (pt.hdr.segment_size + 0x5F & ~0x1F) + 0x20 + 0x40
    logger.info(f"Verifying hash at index {index} (must be {len(pt_data) - 32})")
    assert index == len(pt_data) - 32
    hmac.update(pt_data[:index])
    hmac_hash = hmac.finalize()
    logger.info(f"Hashes match: {hmac_hash == pt.hash}")
    logger.info(f" - expected hash: {hmac_hash.hex()}")
    logger.info(f" - found hash: {pt.hash.hex()}")
    assert hmac_hash == pt.hash

    # skip existing data
    print(pt)
    argv.flash.seek(len(pt_data) + 0x20)
    argv.target.write(CALIBRATION_PATTERN)
    argv.target.write(b"\xff" * 16)
    argv.target.write(pt_data)
    argv.target.write(argv.flash.read())
    logger.info("Done")

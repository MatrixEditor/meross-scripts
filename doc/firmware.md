# Device & Chip Deep Dive

> **Note**
> The information presented here is supported by the [AmebaZII Application Docs](https://github.com/Ameba-AIoT/ameba-rtos-z2/blob/main/doc/AN0500_Realtek_Ameba-ZII_Application_Note.pdf), [AmebaZII Datasheet](https://github.com/Ameba-AIoT/ameba-rtos-z2/blob/main/doc/Realtek_AmebaZII%2B_Datasheet_v1.1.pdf),
> and the detailed structure definitions provided by [ltchiptool](https://github.com/libretiny-eu/ltchiptool).

### Hidden Commands: More Than Meets the Eye

In my exploration of this device, I gained access to a persistent shell through the UART pins (as detailed in the [Teardown](teardown.md) guide). This shell provided access to several utility commands, but there were some surprises along the way.

For a full list of these standard commands, you can refer to the [command examples](https://github.com/bytespider/Meross/blob/develop/teardown/README.md) by Bytespider.

Upon further inspection, I discovered that the device runs on an RTOS from AmebaIoT, which includes a set of hidden system commands not typically found in standard utility sets. These commands are available through the shell (specifically tested on firmware 6.1.8). More details on the system commands can be found in the [Ameba AT-Commands documentation](https://github.com/Ameba-AIoT/ameba-rtos-z2/blob/main/doc/AN0075%20Realtek%20Ameba-all%20at%20command%20v2.0.pdf).

For instance, there are commands that are able to control the wifi settings(`ATWx`). These allow you to shut down an open wifi AP and create a new secured one with a passphrase. However, this new AP remains visible only while the device is online. Once it goes offline, the AP disappears.

---

### ⚠️ The Danger Zone: A Command You Should *Definitely* Not Run

Now, for the fun part. **There's a special, undocumented command** hidden in the depths of the RTOS source code.

<details>
<summary> ⚠️ <b>Warning</b> ⚠️ Open this only if you know what you are doing!</summary>

There’s one command, however, that is not publicly documented and comes with significant risks. This hidden command, `ATXX`, is embedded in the source code of the RTOS (`ameba-rtos-z2/component/common/api/at_cmd/atcmd_sys.c`). It’s used by the AmebaZII PGTool to flash new firmware, particularly in the function `select_download_mode`.

</details>

This command is extremely powerful, but it should be handled with care. If you run this command via UART, there’s a very real risk of bricking the device. It’s essential to understand its function before considering using it.


> **Important:** Running this command will almost certainly brick your device. Proceed with extreme caution, as the consequences are irreversible.  Don’t say I didn’t warn you.

The command itself is quite simple, but its impact is severe. The C code that controls it looks like this:

```c
void fCMD(void *arg) {
    // ...
    flash_t flash_Ptable;
    device_mutex_lock(RT_DEV_LOCK_FLASH);
    flash_erase_sector(&flash_Ptable, 0x00000000); // <-- dangerous
    device_mutex_unlock(RT_DEV_LOCK_FLASH);
    sys_reset();
    // ...
}
```
What happens here is that it *deletes the first sector of the flash*. This sounds pretty harmless, right? WRONG. That first sector happens to contain the partition table and some flash calibration data. Without this data, the device becomes unusable.

The result looks something like this:
```bash
# <the command>

== Rtl8710c IoT Platform ==
Chip VID: 5, Ver: 1
ROM Version: v2.1
[BOOT Err] Parttition Table Header(Plain Text) Verification Err!
StartUp@0x0: Invalid RAM Img Signature!

$8710c>
```

At this point, the device enters fallback mode, and the absence of the partition table renders it inoperable. The partition table is used by the ROM bootloader to load the RAM bootloader, so without it, the device cannot proceed.



#### Fallback CLI Commands

The fallback CLI provides several powerful commands that allow for direct interaction with the device at a low level. Below is a list of the available commands you can try, with `?` or `help` to view the full set.

```
DB
	DB <Address, Hex> <Len, Dec>:
	Dump memory byte or Read Hw byte register

DHW
	DHW <Address, Hex> <Len, Dec>:
	Dump memory helf-word or Read Hw helf-word register;

DW
	DW <Address, Hex> <Len, Dec>:
	Dump memory word or Read Hw word register;

EB
	EB <Address, Hex> <Value, Hex>:
	Write memory byte or Write Hw byte register
	Supports multiple byte writting by a single command
	Ex: EB Address Value0 Value1

EW
	EW <Address, Hex> <Value, Hex>:
	Write memory word or Write Hw word register
	Supports multiple word writting by a single command
	Ex: EW Address Value0 Value1

WDTRST (reboot)
	WDTRST
	To trigger a reset by WDT timeout

fwd
	fwd <tx_pin> <rx_pin> <baud_rate> <parity> <flow ctrl>
	    <flash_io> <flash_pin> <flash_offset_4K_aligned>:
	To download Flash image over UART

ceras
	ceras <io_mode> <pin_sel>
	Flash chip erase

seras
	seras <offset> <len> <io_mode> <pin_sel>
	Flash sector erase

efotp
	Internal cmd.

history
    A history of all entered commands since boot
```

For example, the `DB` command allows you to read bytes from an **arbitrary** memory location
within the chip. This includes not just the flash memory but the entire chip memory, as
outlined in the device’s documentation.

#### Download Mode CLI

If you enter download mode, following the guide by [ltchiptool](https://github.com/libretiny-eu/ltchiptool),
you’ll gain access to additional commands. These commands provide various functionalities for
interacting with the device. Here’s a list of the commands identified so far:

```
ping
    Ping back

uboot
    (Command unclear – documentation needed)

fwdram
    Firmware download (RAM)

disc
    Disconnect and reboot

seras
    (Same as in fallback mode)

ceras
    (Same as in fallback mode)

hashq
    Calculate hash (refer to ltchiptool documentation)

hashs
    (Refer to ltchiptool documentation)

otu2x
    otu2x <flash_io> <flash_pin>
    (Function unclear – documentation needed)

otu2
    otu2 <flash_io> <flash_pin> <fw_idx>
    (Function unclear – documentation needed)

otu1
    otu1 <flash_io> <flash_pin>

fwd
    Firmware download (Flash)

ucfg
    UART configuration
```

### Missing Partition Table: A Closer Look at the Flash

Now, let’s revisit the issue of the missing partition table. If we examine the first bytes of the
chip’s flash memory, we see the following:
```
$8710c>DB 0x98000000 32

 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
98000000: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
98000010: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
...
98000060: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
98000070: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
98000080: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
98000090: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
980000A0: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
980000B0: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
```

As you can see, the memory is completely filled with `ff` values, indicating that everything has been erased. This includes the partition table and other possibly critical data, making the device
inoperable unless recovered with appropriate tools.

### Repairing the Partition Table

Before attempting to recover the partition table, it’s essential to understand its structure. Fortunately, AmebaIoT has published the SDK for building applications for the AmebaZ2 module on [Github](https://github.com/orgs/Ameba-AIoT/repositories). By searching the code base for the error message related to the partition table:.

```bash
grep -r 'Partt'
grep: ameba-rtos-z2/component/soc/realtek/8710c/misc/bsp/lib/common/GCC/lib_soc_is.a: binary file matches
```

It turns out that `lib_soc_is.a` contains multiple object files (not stripped), one of which includes the `otf_get_partition_tbl` function within `encrypt_image_lib_soc.o`. This function is responsible for verifying the partition table.

```
$8710c>EB 0x98000068 0
0x98000068 = 0x00
$8710c>DB 0x98000060 96

 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
98000060: ff ff ff ff ff ff ff ff 00 ff ff ff ff ff ff ff     ................
98000070: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
98000080: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
98000090: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
980000A0: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
980000B0: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
```

After modifying the partition table, triggering a reboot results in the following new error:
```
$8710c>WDTRST

== Rtl8710c IoT Platform ==
Chip VID: 5, Ver: 1
ROM Version: v2.1
[BOOT Err]Parttiton Table Size too big!
StartUp@0x0: Invalid RAM Img Signature!
```


#### Custom Partition Table

After examining the ROM bootloader code and reviewing the excellent write-up by [ltchiptool](https://github.com/libretiny-eu/ltchiptool) on internal structures, I could summarize the process for recovering the partition table. To ensure the integrity of the table, we need to calculate a hash signature using HMAC with SHA256. This is where the private key comes into play.

Fortunately, Meross has used the default key to calculate the hash, which can be found at address `0x00003b84` in the ROM:
```
47E5661335A4C5E0A94D69F3C737D54F2383791332939753EF24279608F6D72B
```

The test script [test_create_partition_table.py](../tests/test_create_partition_table.py) generates a new partition table using information derived from the flash dump. You can refer to the actual code for more details on how the new table is built. However, the outcome of flashing the new partition table, along with the flash calibration pattern to `0x98000000`, is somewhat underwhelming:

1. **Flash the New Partition Table**
	```bash
	ltchiptool flash write --length 4096 rtl8720cf-flash.bin.patched -f ambz2
	I: Available COM ports:
	I: |-- ttyUSB0 - USB to UART Bridge Controller - Silicon Labs (10C4/EA60)
	I: |   |-- Selecting this port. To override, use -d/--device
	I: Detected file type: Realtek AmebaZ2 Flash Image
	I: Connecting to 'Realtek AmebaZ2' on /dev/ttyUSB0 @ 115200
	I: |-- Success! Chip info: RTL8720CF
	I: Writing 'rtl8720cf-flash.bin.patched'
	I: |-- Start offset: 0x0 (auto-detected)
	I: |-- Write length: 62.2 KiB
	I: |-- Skipped data: 0 B (auto-detected)
	[################################################################]  100%          I: Transmission successful (ACK received).
	I: Transmission successful (ACK received).

	I: |-- Finished in 7.821 s
	```

2. **Reboot the Device**
	After flashing the new partition table, reboot the device:
	```bash
	$8710c>WDTRST

	== Rtl8710c IoT Platform ==
	Chip VID: 5, Ver: 1
	ROM Version: v2.1

	== Boot Loader ==
	Dec 16 2019:12:13:23
	[MISC Err]boot_get_load_fw_idx: failed!
	[MISC Err]boot_load: Get load FW index err
	Boot Load Err!
	```

The result: The device fails to boot correctly, and the error indicates a failure in loading the firmware index.

---

There’s still work to be done here, especially around rebuilding the complete flash image. Until a suitable tool is available to restore the flash completely, this topic will remain a work in progress.

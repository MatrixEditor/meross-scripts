# Meross Scripts

> [!NOTE]
> The tools in this repository are not feature-complete and are not intended
> to be. For more comprehensive libraries, check out [meross-iot](https://github.com/albertogeniola/MerossIot)
> and [meross_lan](https://github.com/krahabb/meross_lan)

This repository is built upon research and tools from the following excellent projects:
* [Meross](https://github.com/bytespider/Meross) – Initial access
* [meross-iot](https://github.com/albertogeniola/MerossIot) – Detailed protocol reference
* [ltchiptool](https://github.com/libretiny-eu/ltchiptool) – Flash structure details
* [Ameba-AIoT](https://github.com/orgs/Ameba-AIoT/repositories) – Chip documentation

### Documents

This repository contains tools and additional information regarding hidden functionalities:

* [Tools & Examples](doc/tools.md)
* [Device & Chip Deep Dive](doc/firmware.md) (*or: how to brick and unbrick your device*)
* [Teardown & Pinout](doc/teardown.md)

Most important conclusions:

- Meross uses no encryption in their firmware and within the flash, allowing to extract all possible secrets as plain text
- The serial shell includes special commands that may brick your device
- Using the Cloud API it is possible to register dummy devices which can be used to retrieve the firmware image


### Key Findings

- Meross' firmware is **not encrypted**, meaning all secrets stored within the firmware and flash can be easily extracted as plain text.
- The serial shell includes **special commands** that, if used incorrectly, may brick your device.
- It is possible to register devices using the Cloud API without providing
  internal network data (see [Tools - Device Linking](doc/tools.md#device-linking))

### Disclaimer

This repository and its associated tools are not affiliated with, endorsed by, or connected to Meross or any of its parent companies. The tools and research presented here are for educational and informational purposes only. Use them at your own risk. The author(s) of this repository do not take responsibility for any damage, data loss, or other issues caused by using the tools provided.

## License

Distributed under the MIT License. See LICENSE for more information.
# Tools

### Local Device Interaction

#### Gathering Device Information

To list common device information there is a command named `info`. It will
return the following information:

* `userId`: currently specified User-Id
* `fwVersion`, `hwVersion`: firmware and hardware version
* `UUID`: currenctly active UUID
* `MAC`: mac address
* `mqttClientId`: device's MQTT client id
* `mqttUsername`, `mqttPassword`: device's MQTT credentials
* `cloudServer`: currently specified cloud server

#### Local API

To interact with the HTTP API on the local device, the `query` too can be
utilized similar to `curl`.

Example:
```bash
$ mrs device query System.Appliance.All
{
    # ...
}
```

The request method can be changed with `-X`:
```bash
$ mrs device query -X PUSH System.Control.Unbind [--key $SHARED_KEY] [--payload '{}']
```

#### Setup (bind) a device

There's a special command with similar functionality to the setup tool
provided in [Meross (Bytespider)](https://github.com/bytespider/Meross).
It can be used to configure the shared key, MQTT server and the Wifi
network.

Example:
```bash
# set MQTT server
$ mrs device bind --host 10.10.10.1 --mqtt-host 127.0.0.1:8883 --user-id 1234
# set Wifi network
$ mrs device bind --host 10.10.10.1 --wifi-ssid $SSID --wifi-pass $PASS
```

> [!TIP]
> You can use the configuration JSON file to store the Wifi Ssid and password
> instead of providing them as arguments.

#### Reset (unbind) a device

As simple as binding a device, removing the device from the local network
can be done wirh ease using `unbind`:

```bash
$ mrs device unbind --host $DEVICE_IP
```
### Cloud Interaction

#### SignUp (Registration)

To register a new meross account one can simply use the API without any
extra kind of verification (as of end 2024). Thus, a simple APi request
registers a functionable account:

```bash
$ mrs cloud signup --host 'iot.meross.com' -U 'email' -p '' -use-encryption
```

> [!TIP]
> All attributes can be placed in the configuration file so that `mrs cloud signup` is enough to create a new account.

The retrieved token, user-id and shared key are updated in the local
configuration file if enabled.

#### SignIn

Login is as easy as signup - using the stored credentials only
the command itself must be typed.

```bash
$ mrs cloud login --host $SERVER
```

#### Logout

To invalidate an authentication token use the `logout` command:

```bash
$ mrs cloud logout --host $SERVER
```


#### Firmware Listing

To get an overview of devices that can be upgraded, the firmware listing
tool will give you the update URL mapped to the device Uuid. The output
will contain so-called *common firmwares* and *subfirmwares*.

```bash
$ mrs cloud firmware --host $SERVER --token $TOKEN
                                                                          Common Firmwares
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Uuid                             ┃ Type-SubType ┃ Version ┃ Url                                                                ┃ MD5                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx │ MSS210-US    │ 6.2.3   │ http://static-file.meross.com/staticfile/1635133372731/7078520.bin │ 5c3640981ae2a00b569467bb1b5d0b66 │
└──────────────────────────────────┴──────────────┴─────────┴────────────────────────────────────────────────────────────────────┴──────────────────────────────────┘
I : No sub firmwares found
```

#### Device Listing

To list all devices that are bound to the current cloud account, use `cloud devices list`.

```bash
$ mrs cloud devices list --host $SERVER --token $TOKEN
                                     Devices
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ UUID                             ┃ Name       ┃ Type      ┃ Firmware/Hardware ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx │ Smart Plug │ MSS210-US │ 6.1.8/6.0.0       │
└──────────────────────────────────┴────────────┴───────────┴───────────────────┘
```


#### Device Linking

Instead of using the app to bind a device to your cloud account, it is possible to use the `add` module to register a device without having to
use the app.

As of now, this command can only be used if a connection to the local
device is stable.

```bash
$ mrs cloud devices add --device-ip $IP --host $SERVER --mqtt-domain $MQTT_SERVER --user-id $USER_ID --uuid
```

This command will first

1. Query the device for hardware and firmware requirements
2. Connect to the MQTT broker and publish a `Appliance.Control.Bind` request
3. Registers the device into the cloud account by sending its Uuid


> [!TIP]
> All command arguments can be specified in the configuration file.


### AmebaZII Chip Tools

#### Read Memory

Using the fallback mode of the RTL7820 chip, we can read all memory regions
of the chip.

```bash
mrs -v chip read --timeout 0.1 0x0000 0x1000 -o data.rom.bin
Reading... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
```

> [!WARNING]
> Don't use this tool to dump the complete flash or large regions
> of memory. Use the more stable and professional [ltchiptool](https://github.com/libretiny-eu/ltchiptool):
> ```bash
> $ ltchiptool flash read realtek-ambz2 $TARGET
> ```

#### On-Chip Fallback Console

In order to get a fallback console, you need to either [brick the device]() or enter the download mode using the steps described by `ltchiptool`.

```bash
$ mrs chip console
$8710c>DB 0x100004F0 32

 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
100004F0: bf 87 cc dd 2f d9 b2 24 d3 b7 97 5a b0 d1 63 21     ..../..$...Z..c!
10000500: 85 f4 51 fd 23 a5 53 81 5d f8 ef cb ff 6c 05 7b     ..Q.#.S.]....l.{
```

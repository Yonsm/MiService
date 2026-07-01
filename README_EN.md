# MiService

[中文](README.md) | **English**

![PyPI](https://img.shields.io/pypi/v/miservice)
![License](https://img.shields.io/badge/license-MIT-blue)

XiaoMi Cloud Service for mi.com — A Python library and CLI for Xiaomi Cloud services.

Supports Xiaomi account login (with OTP two-factor authentication), MiIO/MIoT device control, and MiNA XiaoAi Speaker TTS broadcast.

## Features

- Xiaomi account login and service token management (supports SMS/Email OTP two-factor authentication)
- MiIO protocol device control (property read/write, action invocation)
- MIoT Spec interface documentation queries (supports text/python formatted output (raw dict by default))
- MiNA XiaoAi Speaker control: TTS broadcast, volume, playback control, status queries, AI response retrieval
- CLI tool `miservice` for one-line device operations; also supports `python -m miservice`
- Zero hard dependencies; `aiohttp` is optional (falls back to built-in `biohttp` when not installed)

## Installation

```bash
pip3 install miservice

# Optional: install aiohttp for better async HTTP performance
pip3 install aiohttp
```

Requires Python 3.8+.

## Library Structure

```
MiService: XiaoMi Cloud Service
  |
  |-- MiAccount: Account login and token management
  |     |-- Username/password login
  |     |-- OTP two-factor authentication (SMS/Email)
  |     |-- Service token persistence (~/.mi.token)
  |
  |-- MiIOService: MiIO service (sid=xiaomiio)
  |     |-- MiIO protocol requests (signing/encryption)
  |     |-- MIoT property get/set/action invocation
  |     |-- Device list queries
  |     |-- Home/room hierarchy queries
  |     |-- MIoT Spec interface documentation queries
  |     |-- MIoT data decryption
  |
  |-- MiNAService: MiAI service (sid=micoapi)
  |     |-- XiaoAi Speaker device list
  |     |-- TTS broadcast / volume control
  |     |-- Playback control (pause/stop/resume/URL play/single-track loop)
  |     |-- Playback status queries
  |     |-- Latest AI response retrieval
  |     |-- Auto-detection of device models (some models use play_music API)
  |
  |-- miio_command: MiIO command-style interface
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MI_USER` | Yes | Xiaomi account username |
| `MI_PASS` | Yes | Xiaomi account password |
| `MI_DID` | No | Device ID or device name (required when operating devices; also used by MiNA device-level commands to locate the target speaker) |

## CLI Usage

```
MiService 3.0.1 - XiaoMi Cloud Service

Usage: The following variables must be set:
           export MI_USER=<Username>
           export MI_PASS=<Password>
           export MI_DID=<Device ID|Name>

Get Props: miservice <siid[-piid]>[,...]
           miservice 1,1-2,1-3,1-4,2-1,2-2,3
Set Props: miservice <siid[-piid]=[#]value>[,...]
           miservice 2=60,2-1=#60,2-2=false,2-3="null",3=test
Do Action: miservice <siid[-piid]> <arg1|[]> [...]
           miservice 2 []
           miservice 5 Hello
           miservice 5-4 Hello 1

Call MIoT: miservice <cmd=prop/get|/prop/set|action> <params>
           miservice action '{"did":"267090026","siid":5,"aiid":1,"in":["Hello"]}'

Call MiIO: miservice /<uri> <data>
           miservice /home/device_list '{"getVirtualModel":false,"getHuamiDevices":1}'

Devs List: miservice list [name_keyword|full] [getVirtualModel=false|true] [getHuamiDevices=0|1]
           miservice list Light true 0
           miservice list full

Home List: miservice home [name_keyword|full]
           miservice home
           miservice home full
           miservice home 我的家

MIoT Spec: miservice spec [model_keyword|type_urn] [text|python]
           miservice spec
           miservice spec speaker
           miservice spec xiaomi.wifispeaker.lx04
           miservice spec xiaomi.wifispeaker.lx04 text
           miservice spec urn:miot-spec-v2:device:speaker:0000A015:xiaomi-lx04:1

MIoT Decode: miservice decode <ssecurity> <nonce> <data> [gzip]

MiNA Commands:
           miservice mina            # List MiNA devices
           miservice mina <text>     # TTS broadcast to all devices
           miservice mina pause      # Pause playback
           miservice mina stop       # Stop playback
           miservice mina play       # Resume playback
           miservice mina play <url> # Play audio from URL
           miservice mina loop <url> # Play URL on single-track loop
           miservice mina volume <n> # Set volume (0-100)
           miservice mina status     # Get playback status
           miservice mina ask        # Get latest AI response
```

> You can also run `python -m miservice` with the same arguments as the `miservice` command.

### Debug Logging

Control the log level with the `-v` flag (0–5):

```bash
miservice -v5 list        # DEBUG level
miservice -v2 list        # ERROR level
miservice -v3 list        # WARN level
miservice list            # Default WARNING level
```

## Examples

### 1. Set Account

```bash
export MI_USER=<Username>
export MI_PASS=<Password>
```

### 2. Query Device List

```bash
miservice list
```

Displays the list of devices under your account, including name, model, DID, and token.

### 3. Set DID

```bash
export MI_DID=<Device ID|Name>
```

The DID comes from the device list query result, or you can use the device name directly.

### 4. Query Device Interface Documentation

```bash
miservice spec xiaomi.wifispeaker.lx04 text
```

Queries the MIoT interface capabilities of the device, categorized into property get, property set, and action invocation. Omitting `text`/`python` returns the raw spec dict as-is instead of a formatted view.

### 5. Query Volume Property

```bash
miservice 2-1
```

`2` is the `siid`, `1` is the `piid` (if piid is `1`, it can be omitted). These can be found in the spec interface description.

### 6. Set Volume Property

```bash
miservice 2=#60
```

The value type depends on the interface documentation:
- `#` forces a text type; you can also use single quotes `'` and double quotes `"` to force text type (single or paired quotes work)
- Without a type hint, the value is auto-detected; possible results are JSON `null`, `false`, `true`, integer, float, or text

### 7. Action Invocation: TTS Broadcast and Execute Text

The following command makes the XiaoAi Speaker say "Hello":
```bash
miservice 5 Hello
```

Here `5` is the `siid`, and the `aiid` is omitted (defaults to `1`).

The following command is equivalent to saying "XiaoAi, check the weather" to the speaker:
```bash
miservice 5-4 "Check the weather" 1
```

Here `1` means the device should respond verbally. To execute silently (no speaker response):
```bash
miservice 5-4 "Turn off the light" 0
```

If there are no arguments, pass `[]` as a placeholder.

### 8. XiaoAi Speaker Control (MiNA)

`miservice mina` provides TTS broadcast and playback control for XiaoAi Speakers. Without arguments, it lists MiNA devices:

```bash
miservice mina                      # List MiNA devices
```

Send TTS broadcast to all XiaoAi Speakers:

```bash
miservice mina "Hello World"
```

Device-level commands (pause/stop/resume/URL play/single-track loop/volume/status/AI response) require `MI_DID` to locate the target speaker (`MI_DID` corresponds to `miotDID` in the device list):

```bash
export MI_DID=<miotDID>
miservice mina pause                # Pause
miservice mina stop                 # Stop
miservice mina play                 # Resume playback
miservice mina play <url>           # Play specified URL (list loop)
miservice mina loop <url>           # Single-track loop URL
miservice mina volume 50            # Set volume 0-100
miservice mina status               # Query playback status
miservice mina ask                  # Get latest AI response
```

> Note: With `mina <text>`, if the text happens to match a subcommand name (e.g., `pause`), it will be treated as a subcommand. To broadcast such text, use quotes or add a prefix, e.g., `miservice mina "Pause for a moment"`.

## Library Usage

```python
import asyncio
from miservice import MiAccount, MiIOService, MiNAService

async def main():
    account = MiAccount(None, 'username', 'password', '~/.mi.token')

    # Query device list
    io_service = MiIOService(account)
    devices = await io_service.device_list()
    print(devices)

    # Get device property
    value = await io_service.miot_get_prop('device_id', (2, 1))
    print(value)

    # Set device property
    code = await io_service.miot_set_prop('device_id', (2, 1), 60)
    print(code)

    # XiaoAi Speaker TTS
    na_service = MiNAService(account)
    devices = await na_service.device_list()
    if devices:
        device_id = devices[0]['deviceID']
        await na_service.text_to_speech(device_id, 'Hello')

        # Playback control
        await na_service.player_set_volume(device_id, 50)   # Set volume
        await na_service.player_pause(device_id)            # Pause
        await na_service.player_play(device_id)             # Resume
        await na_service.play_by_url(device_id, 'http://.../music.mp3')  # Play URL (auto-detect model)
        await na_service.player_set_loop(device_id, 0)      # 0=single loop, 1=list loop

        # Playback status and AI response
        status = await na_service.player_get_status(device_id)
        messages = await na_service.get_latest_ask(device_id)

asyncio.run(main())
```

## License

[MIT](LICENSE)

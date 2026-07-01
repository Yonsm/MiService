# MiService

**中文** | [English](README_EN.md)

[![PyPI](https://img.shields.io/pypi/v/miservice)](https://pypi.org/project/miservice/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

XiaoMi Cloud Service for mi.com — 小米云服务 Python 库与命令行工具。

支持小米账号登录（含 OTP 两步验证）、MiIO/MIoT 设备控制、MiNA 小爱音箱 TTS 播报等功能。

## 功能

- 小米账号登录与服务令牌管理（支持 SMS/Email OTP 两步验证）
- MiIO 协议设备控制（属性读取/设置、动作调用）
- MIoT Spec 接口文档查询（支持 text/python 格式化输出（不指定时返回原始 dict））
- MiNA 小爱音箱控制：TTS 语音播报、音量、播放控制、状态查询、AI 应答获取
- 命令行工具 `miservice`，一行命令操作设备；亦支持 `python -m miservice`
- 零硬依赖，`aiohttp` 为可选依赖（未安装时自动使用内置 `biohttp` 回退）

## 安装

```bash
pip3 install miservice

# 可选：安装 aiohttp 以获得更好的异步 HTTP 性能
pip3 install aiohttp
```

要求 Python 3.8+。

## 库结构

```
MiService：XiaoMi Cloud Service
  |
  |-- MiAccount：账号登录与令牌管理
  |     |-- 用户名密码登录
  |     |-- OTP 两步验证（SMS/Email）
  |     |-- 服务令牌持久化（~/.mi.token）
  |
  |-- MiIOService：MiIO 服务 (sid=xiaomiio)
  |     |-- MiIO 协议请求（签名/加密）
  |     |-- MIoT 属性获取/设置/动作调用
  |     |-- 设备列表查询
  |     |-- 家庭/房间层级查询
  |     |-- MIoT Spec 接口文档查询
  |     |-- MIoT 数据解密
  |
  |-- MiNAService：MiAI 服务 (sid=micoapi)
  |     |-- 小爱音箱设备列表
  |     |-- TTS 语音播报 / 音量控制
  |     |-- 播放控制（暂停/停止/继续/URL 播放/单曲循环）
  |     |-- 播放状态查询
  |     |-- 最新 AI 应答获取
  |     |-- 设备型号自动适配（部分机型使用 play_music API）
  |
  |-- miio_command：MiIO 命令风格接口
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `MI_USER` | 是 | 小米账号用户名 |
| `MI_PASS` | 是 | 小米账号密码 |
| `MI_DID` | 否 | 设备 ID 或设备名称（操作设备时必填；MiNA 设备级命令亦用它定位目标音箱） |

## 命令行用法

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

> 也可通过 `python -m miservice` 运行，参数与 `miservice` 命令完全一致。

### 调试日志

通过 `-v` 参数控制日志级别（0-5）：

```bash
miservice -v5 list        # DEBUG 级别
miservice -v2 list        # ERROR 级别
miservice -v3 list        # WARN 级别
miservice list            # 默认 WARNING 级别
```

## 示例

### 1. 设置账号

```bash
export MI_USER=<Username>
export MI_PASS=<Password>
```

### 2. 查询设备列表

```bash
miservice list
```

显示账号下的设备列表，包含名称、型号、DID、Token 等信息。

### 3. 设置 DID

```bash
export MI_DID=<Device ID|Name>
```

DID 来自设备列表的查询结果，也可以直接使用设备名称。

### 4. 查询设备接口文档

```bash
miservice spec xiaomi.wifispeaker.lx04 text
```

查询设备的 MIoT 接口能力描述，分为属性获取、属性设置、动作调用三种。不加 `text`/`python` 时返回原始 spec dict，不做格式化。

### 5. 查询音量属性

```bash
miservice 2-1
```

`2` 为 `siid`，`1` 为 `piid`（如果 piid 为 `1` 则可以省略），可从 spec 接口描述中查得。

### 6. 设置音量属性

```bash
miservice 2=#60
```

参数类型根据接口描述文档确定：
- `#` 是强制文本类型，还可以用单引号 `'` 和双引号 `"` 来强制文本类型（可单个引号，也可以两个）
- 如果不强制文本类型，默认将自动检测类型；可能的检测结果是 JSON 的 `null`、`false`、`true`、整数、浮点数或文本

### 7. 动作调用：TTS 播报和执行文本

以下命令执行后小爱音箱会播报"您好"：
```bash
miservice 5 您好
```

其中 `5` 为 `siid`，此处省略了 `aiid`（默认为 `1`）。

以下命令执行后相当于直接对音箱说"小爱同学，查询天气"：
```bash
miservice 5-4 查询天气 1
```

其中 `1` 表示设备语音回应。如果要执行默默关灯（不要音箱回应）：
```bash
miservice 5-4 关灯 0
```

如果没有参数，请传入 `[]` 保留占位。

### 8. 小爱音箱控制（MiNA）

`miservice mina` 提供小爱音箱的 TTS 播报与播放控制。不带参数时列出账号下的 MiNA 设备：

```bash
miservice mina                      # 列出 MiNA 设备
```

向所有小爱音箱发送 TTS 播报：

```bash
miservice mina 你好世界
```

设备级命令（暂停/停止/继续/URL 播放/单曲循环/音量/状态/AI 应答）需要通过 `MI_DID` 定位目标音箱（`MI_DID` 对应设备列表中的 `miotDID`）：

```bash
export MI_DID=<miotDID>
miservice mina pause                # 暂停
miservice mina stop                 # 停止
miservice mina play                 # 继续播放
miservice mina play <url>           # 播放指定 URL（列表循环）
miservice mina loop <url>           # 单曲循环播放 URL
miservice mina volume 50            # 设置音量 0-100
miservice mina status               # 查询播放状态
miservice mina ask                  # 获取最近一次 AI 应答
```

> 注：`mina <text>` 形式中，若文本恰好为子命令名（如 `pause`），会被视为子命令；如需播报此类文本，请加引号或前缀文字，如 `miservice mina "暂停一下"`。

## 作为库使用

```python
import asyncio
from miservice import MiAccount, MiIOService, MiNAService

async def main():
    account = MiAccount(None, 'username', 'password', '~/.mi.token')

    # 查询设备列表
    io_service = MiIOService(account)
    devices = await io_service.device_list()
    print(devices)

    # 获取设备属性
    value = await io_service.miot_get_prop('device_id', (2, 1))
    print(value)

    # 设置设备属性
    code = await io_service.miot_set_prop('device_id', (2, 1), 60)
    print(code)

    # 小爱音箱 TTS
    na_service = MiNAService(account)
    devices = await na_service.device_list()
    if devices:
        device_id = devices[0]['deviceID']
        await na_service.text_to_speech(device_id, '你好')

        # 播放控制
        await na_service.player_set_volume(device_id, 50)   # 设置音量
        await na_service.player_pause(device_id)            # 暂停
        await na_service.player_play(device_id)             # 继续
        await na_service.play_by_url(device_id, 'http://.../music.mp3')  # 播放 URL（自动适配机型）
        await na_service.player_set_loop(device_id, 0)      # 0=单曲循环, 1=列表循环

        # 播放状态与 AI 应答
        status = await na_service.player_get_status(device_id)
        messages = await na_service.get_latest_ask(device_id)

asyncio.run(main())
```

## 许可证

[MIT](LICENSE)

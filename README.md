# MiService
XiaoMi Cloud Service for mi.com

## Install
```
pip3 install aiohttp aiofiles miservice
```

## Library
```
MiService：XiaoMi Cloud Service
  |
  |-- MiAccount：Account Srvice
  |-- MiBaseService：(TODO if needed)
  |     |
  |     |-- MiIOService：MiIO Service (sid=xiaomiio)
  |     |     |
  |     |     |-- MIoT_xxx：MIoT Service, Based on MiIO
  |     |
  |     |-- MiNAService：MiAI Service (sid=micoapi)
  |     |
  |     |-- MiAPIService：(TODO)
  |-- MiIOCommand：MiIO Command Style Interface
```

## Command Line
```
MiService 2.1.2 - XiaoMi Cloud Service

Usage: The following variables must be set:
           export MI_USER=<Username>
           export MI_PASS=<Password>
           export MI_DID=<Device ID|Name>

Get Props: ./micli.py <siid[-piid]>[,...]
           ./micli.py 1,1-2,1-3,1-4,2-1,2-2,3
Set Props: ./micli.py <siid[-piid]=[#]value>[,...]
           ./micli.py 2=60,2-1=#60,2-2=false,2-3="null",3=test
Do Action: ./micli.py <siid[-piid]> <arg1|[]> [...]
           ./micli.py 2 []
           ./micli.py 5 Hello
           ./micli.py 5-4 Hello 1

Call MIoT: ./micli.py <cmd=prop/get|/prop/set|action> <params>
           ./micli.py action '{"did":"267090026","siid":5,"aiid":1,"in":["Hello"]}'

Call MiIO: ./micli.py /<uri> <data>
           ./micli.py /home/device_list '{"getVirtualModel":false,"getHuamiDevices":1}'

Devs List: ./micli.py list [name=full|name_keyword] [getVirtualModel=false|true] [getHuamiDevices=0|1]
           ./micli.py list Light true 0

MIoT Spec: ./micli.py spec [model_keyword|type_urn] [format=text|python|json]
           ./micli.py spec
           ./micli.py spec speaker
           ./micli.py spec xiaomi.wifispeaker.lx04
           ./micli.py spec urn:miot-spec-v2:device:speaker:0000A015:xiaomi-lx04:1

MIoT Decode: ./micli.py decode <ssecurity> <nonce> <data> [gzip]
```

## 套路，例子：

`请在 Mac OS 或 Linux 下执行，Windows 下要支持也应该容易但可能需要修改？`

### 1. 先设置账号

```
export MI_USER=<Username>
export MI_PASS=<Password>
```

### 2. 查询自己的设备

```
micli.py list
```
可以显示自己账号下的设备列表，包含名称、类型、DID、Token 等信息。

### 3. 设置 DID

为了后续操作，请设置 Device ID（来自上面这条命令的结果）。

```
export MI_DID=<Device ID|Name>
```

### 4. 查询设备的接口文档

查询设备的 MIoT 接口能力描述：
```
micli.py spec xiaomi.wifispeaker.lx04
```
其中分为属性获取、属性设置、动作调用三种描述。

### 5. 查询音量属性

```
micli.py 2-1
```
其中 `2` 为 `siid`，`1` 为 `piid`（如果是 `1` 则可以省略），可从 spec 接口描述中查得。

### 6. 设置音量属性

```
micli.py 2=#60
```

参数类型要根据接口描述文档来确定:
- `#`是强制文本类型，还可以用单引号`'`和双引号`"`来强制文本类型`'`（可单个引号，也可以两个）;
- 如果不强制文本类型，默认将检测类型；可能的检测结果是 JSON 的 `null`、`false`、`true`、`整数`、`浮点数`或者`文本`。

### 7. 动作调用：TTS 播报和执行文本

以下命令执行后小爱音箱会播报“您好”：
```
micli.py 5 您好
```
其中，5 为 `siid`，此处省略了 `aiid`（默认为`1`）。

以下命令执行后相当于直接对对音箱说“小爱同学，查询天气”是一个效果：
```
micli.py 5-4 查询天气 1
```

其中 `1` 表示设备语音回应，如果要执行默默关灯（不要音箱回应），可以如下：
```
micli.py 5-4 关灯 0
```

如果没有参数，请传入`[]`保留占位。

### 8. 其它应用

在扩展插件中使用，比如，参考 [ZhiMsg 小爱同学 TTS 播报/执行插件](https://github.com/Yonsm/ZhiMsg)

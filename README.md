# MiCom
XiaoMi IoT Cloud API for mi.com

MiCloud：小米网账号、MiIO/MiOT/MiNA 云服务 API
  |
  |-- MiAuth：一个账号一个实例，支持多个服务 ID（sid）的 Token 获取
  |-- MiCom：服务基础类
  |   |
  |   |-- MiIOCom：小米 MiIO API，sid=xiaomiio
  |   |     |
  |   |     |-- MIoT_xxx：miot 基于 miio
  |   |
  |   |-- MiNACom：sid=micoapi
  |   |
  |   |-- MiAPICom：待建设
  |-- MiIOCmd：小米 MiIO 的命令式使用工具接口
  |-- MiCli：命令行工具

## MiIO Command Line
```
Usage: The following variables must be set:
           export MI_USER=<username>
           export MI_PASS=<password>
           export MIIO_DID=<deviceId>

Get Props: ./micli.py <siid[-piid]>[,...]
           ./micli.py 1,1-2,1-3,1-4,2-1,2-2,3
Set Props: ./micli.py <siid[-piid]=[#]value>[,...]
           ./micli.py 2=#60,2-2=#false,3=test
Do Action: ./micli.py <siid[-piid]> <arg1> [...] 
           ./micli.py 5 您好
           ./micli.py 5-4 天气 #1

Call MIoT: ./micli.py <cmd=prop/get|/prop/set|action> <params>
           ./micli.py action '{"did":"267090026","siid":5,"aiid":1,"in":["您好"]}'

Call MiIO: ./micli.py /<uri> <data>
           ./micli.py /home/device_list '{"getVirtualModel":false,"getHuamiDevices":1}'

Devs List: ./micli.py list [name=full|name_keyword] [getVirtualModel=false|true] [getHuamiDevices=0|1]
           ./micli.py list 灯 true 0

MiIO Spec: ./micli.py spec [model_keyword|type_urn]
           ./micli.py spec
           ./micli.py spec speaker
           ./micli.py spec xiaomi.wifispeaker.lx04
           ./micli.py spec urn:miot-spec-v2:device:speaker:0000A015:xiaomi-lx04:1
```

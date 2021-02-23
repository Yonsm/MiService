# MiService
XiaoMi Service API for mi.com

## MiSerivce Library
```
MiService：小米网账号、MiIO/MiOT/MiNA 云服务 API
  |
  |-- MiAccount：一个账号一个实例，支持多个服务 ID（sid）的 Token 获取
  |-- MiBaseService：服务基础类
  |   |
  |   |-- MiIOService：小米 MiIO API，sid=xiaomiio
  |   |     |
  |   |     |-- MIoT_xxx：miot 基于 miio
  |   |
  |   |-- MiNAService：sid=micoapi
  |   |
  |   |-- MiAPIService：待建设
  |-- MiIOCommand：小米 MiIO 的命令式使用工具接口
```

## MiSerivce Command Line
```
Usage: The following variables must be set:
           export MI_USER=<username>
           export MI_PASS=<password>
           export MIIO_DID=<deviceId>

Get Props: ./miservice.py <siid[-piid]>[,...]
           ./miservice.py 1,1-2,1-3,1-4,2-1,2-2,3
Set Props: ./miservice.py <siid[-piid]=[#]value>[,...]
           ./miservice.py 2=#60,2-2=#false,3=test
Do Action: ./miservice.py <siid[-piid]> <arg1> [...] 
           ./miservice.py 5 您好
           ./miservice.py 5-4 天气 #1

Call MIoT: ./miservice.py <cmd=prop/get|/prop/set|action> <params>
           ./miservice.py action '{"did":"267090026","siid":5,"aiid":1,"in":["您好"]}'

Call MiIO: ./miservice.py /<uri> <data>
           ./miservice.py /home/device_list '{"getVirtualModel":false,"getHuamiDevices":1}'

Devs List: ./miservice.py list [name=full|name_keyword] [getVirtualModel=false|true] [getHuamiDevices=0|1]
           ./miservice.py list 灯 true 0

MiIO Spec: ./miservice.py spec [model_keyword|type_urn]
           ./miservice.py spec
           ./miservice.py spec speaker
           ./miservice.py spec xiaomi.wifispeaker.lx04
           ./miservice.py spec urn:miot-spec-v2:device:speaker:0000A015:xiaomi-lx04:1
```

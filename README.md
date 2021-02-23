# MiService
XiaoMi Cloud Service for mi.com

## Install
```
pip3 install miservice
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
Usage: The following variables must be set:
           export MI_USER=<username>
           export MI_PASS=<password>
           export MIIO_DID=<deviceId>

Get Props: micli.py <siid[-piid]>[,...]
           micli.py 1,1-2,1-3,1-4,2-1,2-2,3
Set Props: micli.py <siid[-piid]=[#]value>[,...]
           micli.py 2=#60,2-2=#false,3=test
Do Action: micli.py <siid[-piid]> <arg1> [...] 
           micli.py 5 Hello
           micli.py 5-4 Hello #1

Call MIoT: micli.py <cmd=prop/get|/prop/set|action> <params>
           micli.py action '{"did":"267090026","siid":5,"aiid":1,"in":["您好"]}'

Call MiIO: micli.py /<uri> <data>
           micli.py /home/device_list '{"getVirtualModel":false,"getHuamiDevices":1}'

Devs List: micli.py list [name=full|name_keyword] [getVirtualModel=false|true] [getHuamiDevices=0|1]
           micli.py list Light true 0

MiIO Spec: micli.py spec [model_keyword|type_urn]
           micli.py spec
           micli.py spec speaker
           micli.py spec xiaomi.wifispeaker.lx04
           micli.py spec urn:miot-spec-v2:device:speaker:0000A015:xiaomi-lx04:1
```

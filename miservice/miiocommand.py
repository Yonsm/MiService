
from json import loads
from .miioservice import MiIOService


def str2tup(string, sep, default=None):
    pos = string.find(sep)
    return (string, default) if pos == -1 else (string[0:pos], string[pos + 1:])


def str2val(string):
    if string[0] in '"\'#':
        return string[1:-1] if string[-1] in '"\'#' else string[1:]
    elif string == 'null':
        return None
    elif string == 'false':
        return False
    elif string == 'true':
        return True
    elif string.isdigit():
        return int(string)
    try:
        return float(string)
    except:
        return string


def miio_command_help(did=None, prefix='?'):
    quote = '' if prefix == '?' else "'"
    return f'\
Get Props: {prefix}<siid[-piid]>[,...]\n\
           {prefix}1,1-2,1-3,1-4,2-1,2-2,3\n\
Set Props: {prefix}<siid[-piid]=[#]value>[,...]\n\
           {prefix}2=60,2-1=#60,2-2=false,2-3="null",3=test\n\
Do Action: {prefix}<siid[-piid]> <arg1|[]> [...] \n\
           {prefix}2 []\n\
           {prefix}5 Hello\n\
           {prefix}5-4 Hello 1\n\n\
Call MIoT: {prefix}<cmd=prop/get|/prop/set|action> <params>\n\
           {prefix}action {quote}{{"did":"{did or "267090026"}","siid":5,"aiid":1,"in":["Hello"]}}{quote}\n\n\
Call MiIO: {prefix}/<uri> <data>\n\
           {prefix}/home/device_list {quote}{{"getVirtualModel":false,"getHuamiDevices":1}}{quote}\n\n\
Devs List: {prefix}list [name=full|name_keyword] [getVirtualModel=false|true] [getHuamiDevices=0|1]\n\
           {prefix}list Light true 0\n\n\
MIoT Spec: {prefix}spec [model_keyword|type_urn] [format=text|python|json]\n\
           {prefix}spec\n\
           {prefix}spec speaker\n\
           {prefix}spec xiaomi.wifispeaker.lx04\n\
           {prefix}spec urn:miot-spec-v2:device:speaker:0000A015:xiaomi-lx04:1\n\n\
MIoT Decode: {prefix}decode <ssecurity> <nonce> <data> [gzip]\n\
'


async def miio_command(service: MiIOService, did, text, prefix='?'):
    cmd, arg = str2tup(text, ' ')

    if cmd.startswith('/'):
        return await service.miio_request(cmd, arg)

    if cmd.startswith('prop') or cmd == 'action':
        return await service.miot_request(cmd, loads(arg) if arg else None)

    argv = arg.split(' ') if arg else []
    argc = len(argv)
    if cmd == 'list':
        return await service.device_list(argc > 0 and argv[0], argc > 1 and str2val(argv[1]), argc > 2 and argv[2])

    if cmd == 'spec':
        return await service.miot_spec(argc > 0 and argv[0], argc > 1 and argv[1])

    if cmd == 'decode':
        return MiIOService.miot_decode(argv[0], argv[1], argv[2], argc > 3 and argv[3] == 'gzip')

    if not did or not cmd or cmd == '?' or cmd == '？' or cmd == 'help' or cmd == '-h' or cmd == '--help':
        return miio_command_help(did, prefix)

    if not did.isdigit():
        devices = await service.device_list(did)
        if not devices:
            return "Device not found: " + did
        did = devices[0]['did']

    props = []
    setp = True
    for item in cmd.split(','):
        iid, val = str2tup(item, '=')
        if val is not None:
            iid = (iid, str2val(val))
            if not setp:
                return "Invalid command: " + cmd
        elif setp:
            setp = False
        props.append(iid)
    miot = (props[0][0][0] if setp else props[0][0]).isdigit()

    if not setp and miot and argc > 0:
        args = [] if arg == '[]' else [str2val(a) for a in argv]
        return await service.miot_action(did, props[0], args)

    miio_props = service.miio_set_props if setp else service.miio_get_props
    return await miio_props(did, props)

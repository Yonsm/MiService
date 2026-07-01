#!/usr/bin/env python3
import asyncio
import logging
import json
import os
import sys
from pathlib import Path

from miservice import MiAccount, MiNAService, MiIOService, miio_command, miio_command_help

MISERVICE_VERSION = '2.4.0'


async def otp_input(otp_method):
    """Default OTP callback: read verification code from terminal."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, f"Input {otp_method} Code: ")


def usage():
    print("MiService %s - XiaoMi Cloud Service\n" % MISERVICE_VERSION)
    print("Usage: The following variables must be set:")
    print("           export MI_USER=<Username>")
    print("           export MI_PASS=<Password>")
    print("           export MI_DID=<Device ID|Name>\n")
    print(miio_command_help(prefix=sys.argv[0] + ' '))


async def main(args):
    env_get = os.environ.get
    store = os.path.join(str(Path.home()), '.mi.token')
    session = None
    try:
        try:
            from aiohttp import ClientSession
            session = ClientSession()
        except ImportError:
            pass
        account = MiAccount(session, env_get('MI_USER'), env_get('MI_PASS'), store, otp_callback=otp_input)
        if args.startswith('mina'):
            service = MiNAService(account)
            result = await service.device_list()
            if len(args) > 4:
                await service.send_message(result, -1, args[4:])
        else:
            service = MiIOService(account)
            result = await miio_command(service, env_get('MI_DID'), args, sys.argv[0] + ' ')
        if not isinstance(result, str):
            result = json.dumps(result, indent=2, ensure_ascii=False)
        print(result)
    except Exception as e:
        print(e)
    finally:
        if session:
            await session.close()

if __name__ == '__main__':
    argv = sys.argv
    argc = len(argv)
    if argc > 1 and argv[1].startswith('-v'):
        argi = 2
        index = int(argv[1][2]) if len(argv[1]) > 2 else 4
        level = [logging.NOTSET, logging.FATAL, logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG][index]
    else:
        argi = 1
        level = logging.WARNING
    if argc > argi:
        if level != logging.NOTSET:
            _LOGGER = logging.getLogger('miservice')
            _LOGGER.setLevel(level)
            _LOGGER.addHandler(logging.StreamHandler())
        asyncio.run(main(' '.join(argv[argi:])))
    else:
        usage()

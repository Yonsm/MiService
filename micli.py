#!/usr/bin/env python3
from aiohttp import ClientSession
import asyncio
import logging
import json
import os
import sys

from miauth import MiAuth, _LOGGER as _LOGGER1
from miiocom import MiIOCom, _LOGGER as _LOGGER2
from miiocmd import miio_cmd, miio_cmd_help


def usage(did):
    print("Usage: The following variables must be set:")
    print("           export MI_USER=<username>")
    print("           export MI_PASS=<password>")
    print("           export MIIO_DID=<deviceId>\n")
    print(miio_cmd_help(did, sys.argv[0] + ' '))


async def main(username, password, did, text):
    async with ClientSession() as session:
        miauth = MiAuth(session, username, password)
        miiocom = MiIOCom(miauth)
        result = await miio_cmd(miiocom, did, text, sys.argv[0] + ' ')
        if not isinstance(result, str):
            result = json.dumps(result, indent=2, ensure_ascii=False)
        print(result)


if __name__ == '__main__':
    argv = sys.argv
    argc = len(argv)
    username = os.environ.get('MI_USER')
    password = os.environ.get('MI_PASS')
    did = os.environ.get('MIIO_DID')
    if argc > 1 and argv[1].startswith('-v'):
        index = int(argv[1][2]) if len(argv[1]) > 2 else 4
        level = [logging.NOTSET, logging.FATAL, logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG][index]
        argv = argv[1:]
    else:
        level = logging.WARNING
    if argc > 1 and username and password:
        if level != logging.NOTSET:
            _LOGGER1.setLevel(level)
            _LOGGER2.setLevel(level)
            _LOGGER1.addHandler(logging.StreamHandler())
            _LOGGER2.addHandler(logging.StreamHandler())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(username, password, did, ' '.join(argv[1:])))
        loop.close()
    else:
        usage(did)

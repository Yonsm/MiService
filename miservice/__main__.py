#!/usr/bin/env python3
"""MiService CLI - command-line interface for XiaoMi Cloud Services."""

import asyncio
import logging
import json
import os
import sys
from pathlib import Path

from miservice import MiAccount, MiNAService, MiIOService, miio_command, miio_command_help, __version__

_LOG_LEVELS = [logging.NOTSET, logging.FATAL, logging.ERROR,
               logging.WARN, logging.INFO, logging.DEBUG]

_LOGGER = logging.getLogger('miservice')


_MINA_COMMANDS = (
    ('',            '# List MiNA devices'),
    ('<text>',      '# TTS broadcast to all devices'),
    ('pause',       '# Pause playback'),
    ('stop',        '# Stop playback'),
    ('play',        '# Resume playback'),
    ('play <url>',  '# Play audio from URL'),
    ('loop <url>',  '# Play URL on single-track loop'),
    ('volume <n>',  '# Set volume (0-100)'),
    ('status',      '# Get playback status'),
    ('ask',         '# Get latest AI response'),
)


def usage():
    """Print usage/help text and exit."""
    print(f"MiService {__version__} - XiaoMi Cloud Service\n")
    print("Usage: The following variables must be set:")
    print("           export MI_USER=<Username>")
    print("           export MI_PASS=<Password>")
    print("           export MI_DID=<Device ID|Name>\n")
    prefix = sys.argv[0] + ' '
    print(miio_command_help(prefix=prefix))
    print("MiNA Commands:")
    for sub, desc in _MINA_COMMANDS:
        print(f"           {prefix}mina {sub.ljust(11)}{desc}")


def find_device_id(hardware_data: list, mi_did: str) -> str:
    """Map a MI_DID value to the MiNA deviceID string.

    Searches by ``miotDID`` first (for numeric IDs), then falls back
    to matching by ``name`` (for device-name-style MI_DID values).
    """
    target = str(mi_did)
    # Primary: match by miotDID (numeric device ID)
    for h in hardware_data:
        if str(h.get('miotDID', '')) == target:
            device_id = h.get('deviceID')
            if device_id:
                return device_id
    # Fallback: match by device name
    for h in hardware_data:
        if h.get('name', '') == target:
            device_id = h.get('deviceID')
            if device_id:
                return device_id
    raise Exception(f"Device not found with miotDID/name={mi_did}. Use 'miservice mina' to list devices.")


# Mina subcommands that require a specific device
_MINA_DEVICE_COMMANDS = {'pause', 'stop', 'play', 'loop', 'volume', 'status', 'ask'}


async def _run_mina(account: MiAccount, args: str) -> int:
    """Handle MiNA (XiaoAi Speaker) subcommands."""
    service = MiNAService(account)
    devices = await service.device_list()
    if devices is None:
        print("No devices found", file=sys.stderr)
        return 1
    # Reuse the already-fetched device list so play_by_url doesn't re-request it
    await service._init_devices(devices)

    parts = args[5:].strip().split(None, 1)  # split after 'mina'
    subcmd = parts[0] if parts else ''
    subarg = parts[1] if len(parts) > 1 else ''

    # Simple list or TTS broadcast (no specific device needed)
    if not subcmd:
        # Just list devices
        if not devices:
            print("No devices found", file=sys.stderr)
            return 1
        for d in devices:
            print(f"{str(d.get('deviceID', '?')):40s} {str(d.get('miotDID', '?')):12s} {str(d.get('name', '?')):20s} {str(d.get('hardware', '?'))}")
        return 0

    if subcmd not in _MINA_DEVICE_COMMANDS:
        # Treat entire string after 'mina' as TTS text
        message = args[5:].strip()
        result = await service.send_message(devices, -1, message)
        return 0 if result else 1

    # Device-specific commands — need MI_DID to locate the target device
    mi_did = os.environ.get('MI_DID', '')
    if not mi_did:
        print("Error: MI_DID environment variable required for device-specific commands", file=sys.stderr)
        return 1
    device_id = find_device_id(devices, mi_did)

    if subcmd == 'pause':
        result = await service.player_pause(device_id)
    elif subcmd == 'stop':
        result = await service.player_stop(device_id)
    elif subcmd == 'play':
        if subarg:
            result = await service.play_by_url(device_id, subarg)
            if result:
                await service.player_set_loop(device_id, 1)  # list loop
        else:
            result = await service.player_play(device_id)
    elif subcmd == 'loop':
        if not subarg:
            print("Error: loop requires a URL argument", file=sys.stderr)
            return 1
        result = await service.play_by_url(device_id, subarg)
        if result:
            await service.player_set_loop(device_id, 0)  # single loop
    elif subcmd == 'volume':
        if not subarg:
            print("Error: volume requires a value (0-100)", file=sys.stderr)
            return 1
        try:
            vol = int(subarg)
        except ValueError:
            print("Error: volume must be an integer (0-100)", file=sys.stderr)
            return 1
        if not 0 <= vol <= 100:
            print("Error: volume must be 0-100", file=sys.stderr)
            return 1
        result = await service.player_set_volume(device_id, vol)
    elif subcmd == 'status':
        status = await service.player_get_status(device_id)
        if status is not None:
            print(json.dumps(status, indent=2, ensure_ascii=False))
            return 0
        print("Failed to get playback status", file=sys.stderr)
        return 1
    elif subcmd == 'ask':
        messages = await service.get_latest_ask(device_id)
        if messages:
            print(json.dumps(messages, indent=2, ensure_ascii=False))
            return 0
        print("No recent AI responses")
        return 0
    else:
        print(f"Unknown mina command: {subcmd}", file=sys.stderr)
        return 1

    return 0 if result else 1


async def _run(args: str) -> int:
    """Parse CLI arguments, authenticate, and dispatch the requested command."""
    env_get = os.environ.get
    store = os.path.join(str(Path.home()), '.mi.token')
    session = None
    try:
        try:
            from aiohttp import ClientSession
            session = ClientSession()
        except ImportError:
            pass
        account = MiAccount(session, env_get('MI_USER'), env_get('MI_PASS'), store)

        if args == 'mina' or args.startswith('mina '):
            return await _run_mina(account, args)

        service = MiIOService(account)
        result = await miio_command(service, env_get('MI_DID'), args, sys.argv[0] + ' ')
        if not isinstance(result, str):
            result = json.dumps(result, indent=2, ensure_ascii=False)
        print(result)
    except Exception as e:
        _LOGGER.exception("Error: %s", e)
        print(e, file=sys.stderr)
        return 1
    finally:
        if session:
            await session.close()
    return 0


def main():
    """Entry point for the `miservice` console script."""
    argv = sys.argv
    argc = len(argv)
    if argc > 1 and argv[1].startswith('-v'):
        argi = 2
        index = int(argv[1][2]) if len(argv[1]) > 2 else 4
        level = _LOG_LEVELS[max(0, min(index, len(_LOG_LEVELS) - 1))]
    else:
        argi = 1
        level = logging.WARNING
    if argc > argi:
        if level != logging.NOTSET:
            _LOGGER.setLevel(level)
            _LOGGER.addHandler(logging.StreamHandler())
        sys.exit(asyncio.run(_run(' '.join(argv[argi:]))))
    else:
        usage()


if __name__ == '__main__':
    main()
"""Local MiIO device control over the LAN UDP binary protocol (port 54321).

Zero hard dependencies: uses pycryptodome's AES when installed (faster),
otherwise falls back to the pure-Python implementation in aes.py — same
fallback pattern as biohttp.py is for aiohttp.
"""

import asyncio
import struct
from hashlib import md5
from json import dumps, loads
from time import monotonic
from typing import Any, List, Optional, Tuple

from .miiocommand import str2tup, str2val

_PORT = 54321
_HELLO = b'\x21\x31\x00\x20' + b'\xff' * 28

try:
    from Crypto.Cipher import AES as _AES

    def aes_cbc_encrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
        return _AES.new(key, _AES.MODE_CBC, iv).encrypt(data)

    def aes_cbc_decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
        return _AES.new(key, _AES.MODE_CBC, iv).decrypt(data)
except ImportError:
    from .aes import aes_cbc_encrypt, aes_cbc_decrypt


def _pkcs7_pad(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len]) * pad_len


def _pkcs7_unpad(data: bytes) -> bytes:
    return data[:-data[-1]] if data else data


# --- UDP transport -------------------------------------------------------

class _MiIODatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.queue: "asyncio.Queue" = asyncio.Queue()

    def datagram_received(self, data: bytes, addr) -> None:
        self.queue.put_nowait(data)

    def error_received(self, exc: Exception) -> None:
        self.queue.put_nowait(exc)


# --- Local device service --------------------------------------------------

class MiIOLocalService:
    """Talk to a single MiIO device directly over the LAN (no cloud/account)."""

    def __init__(self, ip: str, token: str, timeout: float = 3, retries: int = 3):
        self.ip = ip
        self.timeout = timeout
        self.retries = retries
        self.token = bytes.fromhex(token)
        self.key = md5(self.token).digest()
        self.iv = md5(self.key + self.token).digest()
        self._device_id: Optional[int] = None
        self._stamp = 0
        self._stamp_time = 0.0
        self._id = 0

    async def _exchange(self, packet: bytes) -> bytes:
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            _MiIODatagramProtocol, remote_addr=(self.ip, _PORT))
        try:
            for attempt in range(self.retries):
                transport.sendto(packet)
                try:
                    data = await asyncio.wait_for(protocol.queue.get(), self.timeout)
                except asyncio.TimeoutError:
                    if attempt == self.retries - 1:
                        raise TimeoutError(f"No response from {self.ip}:{_PORT}")
                    continue
                if isinstance(data, Exception):
                    raise data
                return data
            raise TimeoutError(f"No response from {self.ip}:{_PORT}")
        finally:
            transport.close()

    async def hello(self) -> None:
        """Handshake to obtain device_id and the device's stamp (uptime counter)."""
        resp = await self._exchange(_HELLO)
        _magic, _length, _unknown, device_id, stamp = struct.unpack('>HHIII', resp[:16])
        self._device_id = device_id
        self._stamp = stamp
        self._stamp_time = monotonic()

    async def send(self, method: str, params: Optional[list] = None) -> Any:
        """Call a raw miIO method, e.g. send('get_prop', ['power'])."""
        if self._device_id is None:
            await self.hello()
        self._id += 1
        payload = dumps({'id': self._id, 'method': method, 'params': params if params is not None else []}).encode()
        encrypted = aes_cbc_encrypt(self.key, self.iv, _pkcs7_pad(payload))
        stamp = self._stamp + int(monotonic() - self._stamp_time)
        header = struct.pack('>HHIII', 0x2131, 32 + len(encrypted), 0, self._device_id, stamp)
        checksum = md5(header + self.token + encrypted).digest()
        resp = await self._exchange(header + checksum + encrypted)
        body = resp[32:]
        if not body:
            return None
        decrypted = aes_cbc_decrypt(self.key, self.iv, body)
        result = loads(_pkcs7_unpad(decrypted).decode())
        if 'error' in result:
            raise Exception(f"Error {method}: {result['error']}")
        return result.get('result')

    async def get_props(self, props: list) -> list:
        return await self.send('get_prop', props)

    async def get_prop(self, prop: str) -> Any:
        return (await self.get_props([prop]))[0]

    async def set_props(self, props: List[Tuple[str, Any]]) -> list:
        return [await self.set_prop(p[0], p[1]) for p in props]

    async def set_prop(self, prop: str, value: Any) -> Any:
        result = await self.send('set_' + prop, value if isinstance(value, list) else [value])
        return 0 if result and result[0] == 'ok' else result


# --- Simple CLI-style command dispatch, mirrors miiocommand.py -------------

def local_command_help(prefix: str = '?') -> str:
    return f"""\
Get Props: {prefix}<prop>[,...]
           {prefix}power,brightness
Set Props: {prefix}<prop=value>[,...]
           {prefix}power=on,brightness=80

Call Method: {prefix}/<method> [params_json]
             {prefix}/miIO.info
             {prefix}/set_power ["on"]
"""


async def local_command(service: MiIOLocalService, text: str, prefix: str = '?') -> Any:
    """Parse and execute a local miio command string against the given service."""
    cmd, arg = str2tup(text.strip(), ' ')

    if not cmd or cmd in ('?', '？', 'help', '-h', '--help'):
        return local_command_help(prefix)

    if cmd.startswith('/'):
        return await service.send(cmd[1:], loads(arg) if arg else [])

    items = cmd.split(',')
    if '=' in items[0]:
        props = []
        for item in items:
            prop, val = str2tup(item, '=')
            if val is None:
                return "Invalid command: " + cmd
            props.append((prop, str2val(val)))
        return await service.set_props(props)

    return await service.get_props(items)

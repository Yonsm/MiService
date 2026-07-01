"""MiIO/MIoT device control service and protocol utilities."""

from os import urandom, fdopen, replace, unlink
from os.path import join, dirname
from time import time
from base64 import b64encode, b64decode
from hashlib import sha256
from hmac import new as hmac_new
from json import loads, dumps, load, dump
from tempfile import mkstemp, gettempdir
from typing import Optional, Tuple, Any

from .miaccount import UA_MIIO

from logging import getLogger
_LOGGER = getLogger(__package__)

# MIoT spec cache file path
_SPEC_CACHE = join(gettempdir(), 'miservice_miot_specs.json')

# REGIONS = ['cn', 'de', 'i2', 'ru', 'sg', 'us']


def str2iid(iid: str) -> Tuple[int, int]:
    pos = iid.find('-')
    return (int(iid), 1) if pos == -1 else (int(iid[0:pos]), int(iid[pos + 1:]))


def rc4(key: bytes, data: bytes) -> bytes:
    """Pure-Python RC4 (ARC4) implementation — replaces pycryptodome."""
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]
    # Discard first 1024 bytes (RC4 drop, matching pycryptodome usage)
    i = j = 0
    out = bytearray()
    for _ in range(1024):
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
    for byte in data:
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out.append(byte ^ S[(S[i] + S[j]) & 0xFF])
    return bytes(out)


def _atomic_write_json(file_path: str, data) -> None:
    """Atomically write JSON data to avoid race conditions."""
    fd, tmp_path = mkstemp(dir=dirname(file_path) or '.')
    try:
        with fdopen(fd, 'w') as f:
            dump(data, f)
        replace(tmp_path, file_path)
    except Exception:
        unlink(tmp_path)
        raise


class MiIOService:
    """Service client for MiIO/MIoT device API requests."""

    def __init__(self, account=None, region: Optional[str] = None):
        self.account = account
        self.server = f'https://{"" if region is None or region == "cn" else region + "."}api.io.mi.com/app'

    async def miio_request(self, uri: str, data) -> Any:
        if not self.account:
            raise Exception("MiIOService requires an account for API requests")
        def prepare_data(token, cookies):
            cookies['PassportDeviceId'] = token['deviceId']
            return MiIOService.sign_data(uri, data, token['xiaomiio'][0])
        headers = {'User-Agent': UA_MIIO, 'x-xiaomi-protocal-flag-cli': 'PROTOCAL-HTTP2'}
        resp = await self.account.mi_request('xiaomiio', self.server + uri, prepare_data, headers)
        if 'result' not in resp:
            raise Exception(f"Error {uri}: {resp}")
        return resp['result']

    async def miio_get_props(self, did: str, iids):
        # iid: (2,1)|[2,1]|"2-1"|"power"
        if isinstance(iids[0], str):
            if not iids[0][0].isdigit():
                return await self.home_get_props(did, iids)
            iids = [str2iid(i) for i in iids]
        return await self.miot_get_props(did, iids)

    async def miio_set_props(self, did: str, props):
        if isinstance(props[0][0], str):
            if not props[0][0][0].isdigit():
                return await self.home_set_props(did, props)
            props = [(*str2iid(prop[0]), prop[1]) for prop in props]
        return await self.miot_set_props(did, props)

    async def miio_get_prop(self, did: str, iid):
        if isinstance(iid, str):
            if not iid[0].isdigit():
                return await self.home_get_prop(did, iid)
            iid = str2iid(iid)
        return await self.miot_get_prop(did, iid)

    async def miio_set_prop(self, did: str, iid, value):
        if isinstance(iid, str):
            if not iid[0].isdigit():
                return await self.home_set_prop(did, iid, value)
            iid = str2iid(iid)
        return await self.miot_set_prop(did, iid, value)

    async def home_request(self, did: str, method: str, params):
        return await self.miio_request('/home/rpc/' + did, {'id': 1, 'method': method, 'accessKey': 'IOS00026747c5acafc2', 'params': params})

    async def home_get_props(self, did: str, props):
        return await self.home_request(did, 'get_prop', props)

    async def home_set_props(self, did: str, props):
        return [await self.home_set_prop(did, i[0], i[1]) for i in props]

    async def home_get_prop(self, did: str, prop: str):
        return (await self.home_get_props(did, [prop]))[0]

    async def home_set_prop(self, did: str, prop: str, value):
        result = (await self.home_request(did, 'set_' + prop, value if isinstance(value, list) else [value]))[0]
        return 0 if result == 'ok' else result

    async def miot_request(self, cmd: str, params):
        return await self.miio_request('/miotspec/' + cmd, {'params': params})

    async def miot_get_props(self, did: str, iids):
        params = [{'did': did, 'siid': i[0], 'piid': i[1]} for i in iids]
        result = await self.miot_request('prop/get', params)
        return [it.get('value') if it.get('code') == 0 else None for it in result]

    async def miot_set_props(self, did: str, props):
        params = [{'did': did, 'siid': i[0], 'piid': i[1], 'value': i[2]} for i in props]
        result = await self.miot_request('prop/set', params)
        return [it.get('code', -1) for it in result]

    async def miot_get_prop(self, did: str, iid):
        return (await self.miot_get_props(did, [iid]))[0]

    async def miot_set_prop(self, did: str, iid, value):
        return (await self.miot_set_props(did, [(iid[0], iid[1], value)]))[0]

    async def miot_action(self, did: str, iid, args: Optional[list] = None):
        result = await self.miot_request('action', {'did': did, 'siid': iid[0], 'aiid': iid[1], 'in': args or []})
        return result.get('code', -1)

    async def device_list(self, name: Optional[str] = None, getVirtualModel=False, getHuamiDevices=0):
        result = await self.miio_request('/home/device_list', {'getVirtualModel': bool(getVirtualModel), 'getHuamiDevices': int(getHuamiDevices)})
        result = (result or {}).get('list') or []
        if name == 'full':
            return result
        return [{'name': i['name'], 'model': i['model'], 'did': i['did'], 'token': i['token']} for i in result if not name or name in i['name']]

    async def home_list(self, name: Optional[str] = None):
        """Fetch home/room hierarchy with device assignments.

        Args:
            name: Keyword to filter homes by name; 'full' returns the raw
                  API response; None returns all homes with key fields only
                  (id, name, rooms with id/name/dids).

        Returns a list of homes, each containing rooms with their device DIDs.
        Example: [{'id': 123, 'name': '我的家', 'rooms': [{'id': 456, 'name': '客厅', 'dids': [...]}, ...]}, ...]
        """
        result = await self.miio_request('/homeroom/gethome', {})
        if not isinstance(result, list):
            result = (result or {}).get('homelist') or (result or {}).get('list') or []
        if name == 'full':
            return result
        return [{'id': h.get('id'), 'name': h.get('name'), 'rooms': [{'id': r.get('id'), 'name': r.get('name'), 'dids': r.get('dids', [])} for r in h.get('roomlist', [])]} for h in result if not name or name in (h.get('name') or '')]

    async def miot_spec(self, _type: Optional[str] = None, _format: Optional[str] = None):
        """Fetch and optionally format MIoT spec.

        Args:
            _type: Model keyword, exact model name, or URN type. If falsy, returns all specs.
            _format: Output format — 'text' or 'python'. If falsy, returns the raw spec dict.
        """
        if not self.account:
            raise Exception("MiIOService requires an account for API requests")
        # Resolve type if it's not a URN
        if not _type or not _type.startswith('urn'):
            resolved = await self._resolve_spec_type(_type)
            if not isinstance(resolved, str):
                return resolved  # Return dict of matches (or empty dict)
            _type = resolved

        url = 'https://miot-spec.org/miot-spec-v2/instance?type=' + _type
        async with self.account.request(url) as r:
            result = await r.json()

        return self._format_spec(result, _format, url) if _format else result

    async def _resolve_spec_type(self, _type: Optional[str]) -> Any:
        """Resolve a model name/keyword to a MIoT spec URN type string.

        Returns the URN string for a unique match, or a dict of matches
        (possibly empty) when zero or multiple models are found.
        """
        def filter_specs(specs_all):
            if not _type:
                return specs_all
            ret = {}
            for m, t in specs_all.items():
                if _type == m:
                    return {m: t}
                elif _type in m:
                    ret[m] = t
            return ret

        try:
            with open(_SPEC_CACHE) as f:
                result = filter_specs(load(f))
        except (OSError, ValueError):
            result = None

        if not result:
            async with self.account.request('https://miot-spec.org/miot-spec-v2/instances?status=all') as r:
                specs_all = {i['model']: i['type'] for i in (await r.json())['instances']}
                _atomic_write_json(_SPEC_CACHE, specs_all)
                result = filter_specs(specs_all)

        if len(result) != 1:
            return result  # Empty or multiple matches
        return list(result.values())[0]  # Single match -> URN type

    @staticmethod
    def _parse_spec_desc(node: dict) -> Tuple[str, str]:
        """Extract name and comment from a spec node's description."""
        desc = node['description']
        name = ''
        for i in range(len(desc)):
            d = desc[i]
            # CJK delimiters from Xiaomi MIoT spec format
            if d in '-—{「[【(（<《':
                return (name, '  # ' + desc[i:])
            name += '_' if d == ' ' else d
        return (name, '')

    @staticmethod
    def _make_spec_line(siid: int, iid: int, desc: str, comment: str, format: Optional[str], readable: bool = False) -> str:
        value = f"({siid}, {iid})" if format == 'python' else iid
        return f"    {'' if readable else '_'}{desc} = {value}{comment}\n"

    def _format_spec(self, result: dict, _format: Optional[str], url: str) -> str:
        """Format MIoT spec as text or Python enum."""
        str_head, str_srv, str_value = (
            ('from enum import Enum\n\n', '\nclass {}(tuple, Enum):\n', '\nclass {}(int, Enum):\n')
            if _format == 'python' else ('', '{} = {}\n', '{}\n')
        )
        text = '# Generated by https://github.com/Yonsm/MiService\n# ' + url + '\n\n' + str_head
        svcs = []
        vals = []

        for s in result['services']:
            siid = s['iid']
            svc = s['description'].replace(' ', '_')
            svcs.append(svc)
            text += str_srv.format(svc, siid)
            for p in s.get('properties', []):
                name, comment = self._parse_spec_desc(p)
                access = p['access']

                comment += ''.join(['  # ' + k for k, v in [(p['format'], 'string'), (''.join([a[0] for a in access]), 'r')] if k and k != v])
                text += self._make_spec_line(siid, p['iid'], name, comment, _format, 'read' in access)
                if 'value-range' in p:
                    valuer = p['value-range']
                    length = min(3, len(valuer))
                    values = {['MIN', 'MAX', 'STEP'][i]: valuer[i] for i in range(length) if i != 2 or valuer[i] != 1}
                elif 'value-list' in p:
                    values = {i['description'].replace(' ', '_') if i['description'] else str(i['value']): i['value'] for i in p['value-list']}
                else:
                    continue
                vals.append((svc + '_' + name, values))
            if 'actions' in s:
                text += '\n'
                for a in s['actions']:
                    name, comment = self._parse_spec_desc(a)
                    comment += ''.join([f"  # {io}={a[io]}" for io in ['in', 'out'] if a[io]])
                    text += self._make_spec_line(siid, a['iid'], name, comment, _format)
            text += '\n'
        for name, values in vals:
            text += str_value.format(name)
            for k, v in values.items():
                text += f"    {'_' + k if k.isdigit() else k} = {v}\n"
            text += '\n'
        if _format == 'python':
            text += '\nALL_SVCS = (' + ', '.join(svcs) + ')\n'
        return text

    @staticmethod
    def miot_decode(ssecurity: str, nonce: str, data: str, gzip: bool = False):
        decrypted = rc4(b64decode(MiIOService.sign_nonce(ssecurity, nonce)), b64decode(data))
        if gzip:
            try:
                from io import BytesIO
                from gzip import GzipFile
                compressed = BytesIO()
                compressed.write(decrypted)
                compressed.seek(0)
                decrypted = GzipFile(fileobj=compressed, mode='rb').read()
            except OSError:
                # Not gzip-compressed; fall back to the raw decrypted bytes
                pass
        return loads(decrypted.decode())

    @staticmethod
    def sign_nonce(ssecurity: str, nonce: str) -> str:
        m = sha256()
        m.update(b64decode(ssecurity))
        m.update(b64decode(nonce))
        return b64encode(m.digest()).decode()

    @staticmethod
    def sign_data(uri: str, data, ssecurity: str) -> dict:
        if not isinstance(data, str):
            data = dumps(data)
        nonce = b64encode(urandom(8) + int(time() / 60).to_bytes(4, 'big')).decode()
        snonce = MiIOService.sign_nonce(ssecurity, nonce)
        msg = '&'.join([uri, snonce, nonce, 'data=' + data])
        sign = hmac_new(key=b64decode(snonce), msg=msg.encode(), digestmod=sha256).digest()
        return {'_nonce': nonce, 'data': data, 'signature': b64encode(sign).decode()}
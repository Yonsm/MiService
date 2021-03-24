import os
import time
import base64
import hashlib
import hmac
import json
import logging
from .miaccount import MiAccount

_LOGGER = logging.getLogger(__package__)

# REGIONS = ['cn', 'de', 'i2', 'ru', 'sg', 'us']


def gen_nonce():
    """Time based nonce."""
    nonce = os.urandom(8) + int(time.time() / 60).to_bytes(4, 'big')
    return base64.b64encode(nonce).decode()


def gen_signed_nonce(ssecret, nonce):
    """Nonce signed with ssecret."""
    m = hashlib.sha256()
    m.update(base64.b64decode(ssecret))
    m.update(base64.b64decode(nonce))
    return base64.b64encode(m.digest()).decode()


def gen_signature(url, signed_nonce, nonce, data):
    """Request signature based on url, signed_nonce, nonce and data."""
    sign = '&'.join([url, signed_nonce, nonce, 'data=' + data])
    signature = hmac.new(key=base64.b64decode(signed_nonce),
                         msg=sign.encode(),
                         digestmod=hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


def sign_data(uri, data, ssecurity):
    if not isinstance(data, str):
        data = json.dumps(data)
    nonce = gen_nonce()
    signed_nonce = gen_signed_nonce(ssecurity, nonce)
    signature = gen_signature(uri, signed_nonce, nonce, data)
    return {'_nonce': nonce, 'data': data, 'signature': signature}


class MiIOService:

    def __init__(self, account: MiAccount, region=None):
        self.account = account
        self.server = 'https://' + ('' if region is None or region == 'cn' else region + '.') + 'api.io.mi.com/app'

    async def miio_request(self, uri, data):
        def prepare_data(token, cookies):
            cookies['PassportDeviceId'] = token['deviceId']
            return sign_data(uri, data, token['xiaomiio'][0])
        headers = {'User-Agent': 'iOS-14.4-6.0.103-iPhone12,3--D7744744F7AF32F0544445285880DD63E47D9BE9-8816080-84A3F44E137B71AE-iPhone', 'x-xiaomi-protocal-flag-cli': 'PROTOCAL-HTTP2'}
        return (await self.account.mi_request('xiaomiio', self.server + uri, prepare_data, headers))['result']

    async def miot_request(self, cmd, params):
        return await self.miio_request('/miotspec/' + cmd, {'params': params})

    async def miot_get_props(self, did, props):
        params = [{'did': did, 'siid': prop[0], 'piid': prop[1]} for prop in props]
        result = await self.miot_request('prop/get', params)
        return [it.get('value') if it.get('code') == 0 else None for it in result]

    async def miot_set_props(self, did, props):
        params = [{'did': did, 'siid': prop[0], 'piid': prop[1], 'value': prop[2]} for prop in props]
        result = await self.miot_request('prop/set', params)
        return [it.get('code', -1) for it in result]

    async def miot_get_prop(self, did, siid, piid=1):
        return (await self.miot_get_props(did, [(siid, piid)]))[0]

    async def miot_set_prop(self, did, siid, piid, value):
        return (await self.miot_set_props(did, [(siid, piid, value)]))[0]

    async def miot_action(self, did, siid, aiid=1, args=[]):
        return await self.miot_request('action', {'did': did, 'siid': siid, 'aiid': aiid, 'in': args})

    async def miot_control(self, did, siid, iid, value=[]):
        if isinstance(value, list):
            return (await self.miot_action(did, siid, iid, value)).get('code', -1)
        return await self.miot_set_prop(did, siid, iid, value)

    async def device_list(self, name=None, getVirtualModel=False, getHuamiDevices=0):
        result = await self.miio_request('/home/device_list', {'getVirtualModel': bool(getVirtualModel), 'getHuamiDevices': int(getHuamiDevices)})
        result = result['list']
        return result if name == 'full' else [{'name': i['name'], 'model': i['model'], 'did': i['did'], 'token': i['token']} for i in result if not name or name in i['name']]

    async def miot_spec(self, type=None, format=None):
        if not type or not type.startswith('urn'):
            def get_spec(all):
                if not type:
                    return all
                ret = {}
                for m, t in all.items():
                    if type == m:
                        return {m: t}
                    elif type in m:
                        ret[m] = t
                return ret
            import tempfile
            path = os.path.join(tempfile.gettempdir(), 'miservice_miot_specs.json')
            try:
                with open(path) as f:
                    result = get_spec(json.load(f))
            except:
                result = None
            if not result:
                async with self.account.session.get('http://miot-spec.org/miot-spec-v2/instances?status=all') as r:
                    all = {i['model']: i['type'] for i in (await r.json())['instances']}
                    with open(path, 'w') as f:
                        json.dump(all, f)
                    result = get_spec(all)
            if len(result) != 1:
                return result
            type = list(result.values())[0]

        url = 'http://miot-spec.org/miot-spec-v2/instance?type=' + type
        async with self.account.session.get(url) as r:
            result = await r.json()

        if format != 'json':
            STR_EXP = '%s%s = %s\n'
            STR_EXP2 = '%s%s = %s%s\n'
            STR_HEAD, STR_SRV, STR_PROP, STR_VALUE, STR_ACTION = ('from enum import IntEnum\n\n', 'SRV_', 'PROP_', 'class VALUE_{}(IntEnum):\n',
                                                                  'ACTION_') if format == 'python' else ('', '', '  ', '', '  ')
            text = '# Generated by https://github.com/Yonsm/MiService\n# ' + url + '\n\n' + STR_HEAD
            siids = {}
            for s in result['services']:
                siid = s['iid']
                desc = s['description'].replace(' ', '_')
                text += STR_EXP % (STR_SRV, desc, siid)
                piids = {}
                for p in s.get('properties', []):
                    piid = p['iid']
                    desc = p['description'].replace(' ', '_')
                    access = p['access']
                    if 'read' in access:
                        piids[piid] = desc
                    comment = ''.join([' #' + k for k, v in [(p['format'], 'string'), (''.join([a[0] for a in access]), 'r')] if k != v])
                    text += STR_EXP2 % (STR_PROP, desc, piid, comment)
                    if 'value-range' in p:
                        valuer = p['value-range']
                        length = min(3, len(valuer))
                        values = {['MIN', 'MAX', 'STEP'][i]: valuer[i] for i in range(length) if i != 2 or valuer[i] != 1}
                    elif 'value-list' in p:
                        values = {i['description'].replace(' ', '_'): i['value'] for i in p['value-list']}
                    else:
                        continue
                    text += STR_VALUE.format(desc) + ''.join([STR_EXP % ('    ', k, v) for k, v in values.items()])
                if piids:
                    siids[siid] = piids
                for a in s.get('actions', []):
                    desc = a['description'].replace(' ', '_')
                    comment = ''.join([f" #{io}={a[io]}" for io in ['in', 'out'] if a[io]])
                    text += STR_EXP2 % (STR_ACTION, desc, a['iid'], comment)
                text += '\n'
            if format == 'python':
                text += 'ALL_PROPS = ' + str(siids) + '\n'
            result = text
        return result

import os
import time
import base64
import hashlib
import hmac
import json
from .miaccount import MiAccount

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

    async def miot_spec_dict(self):
        import tempfile
        specs_path = os.path.join(tempfile.gettempdir(), 'miservice_miot_specs.json')
        if os.path.exists(specs_path):
            try:
                with open(specs_path) as f:
                    result = json.load(f)
                    if result:
                        return result
            except:
                pass

        async with self.account.session.get('http://miot-spec.org/miot-spec-v2/instances?status=all') as r:
            all = {i['model']: i['type'] for i in (await r.json())['instances']}
            with open(specs_path, 'w') as f:
                json.dump(all, f)
        return all

    async def miot_spec_data(self, urn, format=None):
        url = 'http://miot-spec.org/miot-spec-v2/instance?type=' + urn
        async with self.account.session.get(url) as r:
            data = await r.json()
        if format == 'json':
            return data
        if format == 'lite':
            return {s['description']: {'iid': s['iid']} | {(p['description'] + '=') if 'write' in p['access'] else p['description']: p['iid'] if 'read' in p['access'] else -p['iid'] for p in s.get('properties', [])} | {'@' + a['description']: a['iid'] for a in s.get('actions', [])} for s in data['services']}
        else:
            STR_EXP = '%s%s = %s\n'
            STR_EXP2 = '%s%s = %s%s\n'
            STR_HEAD, STR_SRV, STR_PROP, STR_VALUE, STR_ACTION = ('from enum import IntEnum\n\n', 'SRV_', 'PROP_', 'class VALUE_{}(IntEnum):\n',
                                                                  'ACTION_') if format == 'python' else ('', '', '  ', '', '  ')
            text = '# Generated by https://github.com/Yonsm/MiService\n\n' + STR_HEAD
            for s in data['services']:
                desc = s['description'].replace(' ', '_')
                text += STR_EXP % (STR_SRV, desc, s['iid'])
                for p in s.get('properties', []):
                    desc = p['description'].replace(' ', '_')
                    access = p['access']
                    comment = ''.join([' #' + k for k, v in [(p['format'], 'string'), (''.join([a[0] for a in access]), 'r')] if k != v])
                    text += STR_EXP2 % (STR_PROP, desc, p['iid'], comment)
                    if 'value-range' in p:
                        valuer = p['value-range']
                        length = min(3, len(valuer))
                        values = {['MIN', 'MAX', 'STEP'][i]: valuer[i] for i in range(length) if i != 2 or valuer[i] != 1}
                    elif 'value-list' in p:
                        values = {i['description'].replace(' ', '_'): i['value'] for i in p['value-list']}
                    else:
                        continue
                    text += STR_VALUE.format(desc) + ''.join([STR_EXP % ('    ', k, v) for k, v in values.items()])
                for a in s.get('actions', []):
                    desc = a['description'].replace(' ', '_')
                    comment = ''.join([f" #{io}={a[io]}" for io in ['in', 'out'] if a[io]])
                    text += STR_EXP2 % (STR_ACTION, desc, a['iid'], comment)
                text += '\n'
            return text

    async def miot_spec_for_model(self, model, format=None):
        all = await self.miot_spec_dict()
        return await self.miot_spec_data(all[model], format) if model in all else None

    async def miot_spec(self, urn_or_model=None, format=None):
        if not urn_or_model or not urn_or_model.startswith('urn'):
            all = await self.miot_spec_dict()
            if not urn_or_model:
                return all
            if urn_or_model in all:
                urn_or_model = all[urn_or_model]
            else:
                items = {m: t for m, t in all.items() if urn_or_model in m}
                if len(items) != 1:
                    return items
                urn_or_model = list(items.values())[0]
        return await self.miot_spec_data(urn_or_model, format)

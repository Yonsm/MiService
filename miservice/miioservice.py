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

    async def miot_get_prop(self, did, siid, piid):
        return (await self.miot_get_props(did, [(siid, piid)]))[0]

    async def miot_set_prop(self, did, siid, piid, value):
        return (await self.miot_set_props(did, [(siid, piid, value)]))[0]

    async def miot_action(self, did, siid, aiid, args):
        # if not did:
        #     did = f'action-{siid}-{aiid}'
        result = await self.miot_request('action', {'did': did, 'siid': siid, 'aiid': aiid, 'in': args})
        return result

    async def miot_spec(self, type=None):
        if not type or not type.startswith('urn'):
            async with self.account.session.get('http://miot-spec.org/miot-spec-v2/instances?status=all') as r:
                result = await r.json()
            result = {i['model']: i['type'] for i in result['instances'] if not type or type in i['model']}
            if len(result) != 1:
                return result
            type = list(result.values())[0]
        async with self.account.session.get('http://miot-spec.org/miot-spec-v2/instance?type=' + type) as r:
            return await r.json()

    async def device_list(self, name=None, getVirtualModel=False, getHuamiDevices=0):
        result = await self.miio_request('/home/device_list', {'getVirtualModel': bool(getVirtualModel), 'getHuamiDevices': int(getHuamiDevices)})
        result = result['list']
        return result if name == 'full' else [{'name': i['name'], 'model': i['model'], 'did': i['did'], 'token': i['token']} for i in result if not name or name in i['name']]

import logging

_LOGGER = logging.getLogger(__name__)

# REGIONS = ['cn', 'de', 'i2', 'ru', 'sg', 'us']


class MiIOCom:

    def __init__(self, auth, region=None):
        self.auth = auth
        self.server = 'https://' + ('' if region is None or region == 'cn' else region + '.') + 'api.io.mi.com/app'

    async def request(self, uri, data, relogin=True):
        if self.auth.token is not None or await self.auth.login():  # Ensure login
            _LOGGER.info(f"{uri} {data}")
            r = await self.auth.session.post(self.server + uri, cookies={
                'userId': self.auth.token['userId'],
                'serviceToken': self.auth.token['serviceToken'],
                # 'locale': 'en_US'
            }, headers={
                'User-Agent': self.auth.user_agent,
                'x-xiaomi-protocal-flag-cli': 'PROTOCAL-HTTP2'
            }, data=self.auth.sign(uri, data), timeout=10)
            resp = await r.json(content_type=None)
            code = resp['code']
            if code == 0:
                result = resp['result']
                if result is not None:
                    # _LOGGER.debug(f"{result}")
                    return result
            elif code == 2 and relogin:
                _LOGGER.debug(f"Auth error on request {uri}, relogin...")
                self.token = None  # Auth error, reset login
                return self.request(uri, data, False)
        else:
            resp = "Login failed"
        error = f"Error {uri}: {resp}"
        _LOGGER.error(error)
        raise Exception(error)

    async def miot_request(self, cmd, params):
        return await self.request('/miotspec/' + cmd, {'params': params})

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
            async with self.auth.session.get('http://miot-spec.org/miot-spec-v2/instances?status=all') as r:
                result = await r.json()
            result = {i['model']: i['type'] for i in result['instances'] if not type or type in i['model']}
            if len(result) != 1:
                return result
            type = list(result.values())[0]
        async with self.auth.session.get('http://miot-spec.org/miot-spec-v2/instance?type=' + type) as r:
            return await r.json()

    async def device_list(self, name=None, getVirtualModel=False, getHuamiDevices=0):
        result = await self.request('/home/device_list', {'getVirtualModel': bool(getVirtualModel), 'getHuamiDevices': int(getHuamiDevices)})
        result = result['list']
        return result if name == 'full' else [{'name': i['name'], 'model': i['model'], 'did': i['did'], 'token': i['token']} for i in result if not name or name in i['name']]


import logging
from miauth import MiAuth

_LOGGER = logging.getLogger(__name__)


class MiCom:

    def __init__(self, auth: MiAuth):
        self.auth = auth

    async def request(self, sid, url, data, headers, relogin=True):
        if (self.auth.token and sid in self.auth.token) or await self.auth.login(sid):  # Ensure login
            cookies = {'userId': self.auth.token['userId'], 'serviceToken': self.auth.token[sid]}
            if callable(data):
                data = data(cookies)
            _LOGGER.info(f"{url} {data}")
            method = 'GET' if data is None else 'POST'
            r = await self.auth.session.request(method, url, data=data, cookies=cookies, headers=headers)
            status = r.status
            if status == 200:
                resp = await r.json(content_type=None)
                code = resp['code']
                if code == 0:
                    return resp
                if 'auth' in resp.get('message', '').lower():
                    status = 401
            else:
                resp = await r.text()
            if  status == 401 and relogin:
                _LOGGER.warn(f"Auth error on request {url} {resp}, relogin...")
                self.token = None  # Auth error, reset login
                return await self.request(sid, url, data, headers, False)
        else:
            resp = "Login failed"
        error = f"Error {url}: {resp}"
        _LOGGER.error(error)
        raise Exception(error)

import random
import string
import logging
from .miaccount import MiAccount

_LOGGER = logging.getLogger(__name__)


def get_random(length):
    return ''.join(random.sample(string.ascii_letters + string.digits, length))


class MiBaseService:

    def __init__(self, account: MiAccount):
        self.account = account

    async def request(self, sid, url, data, headers, relogin=True):
        token = await self.account.get_token(sid)
        if token:  # Ensure login
            cookies = {'userId': token['userId'], 'serviceToken': token[sid]}
            if callable(data):
                data = data(token, cookies)
            _LOGGER.info(f"{url} {data}")
            method = 'GET' if data is None else 'POST'
            r = await self.account.session.request(method, url, data=data, cookies=cookies, headers=headers)
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
            if status == 401 and relogin:
                _LOGGER.warn(f"Auth error on request {url} {resp}, relogin...")
                self.token = None  # Auth error, reset login
                return await self.request(sid, url, data, headers, False)
        else:
            resp = "Login failed"
        error = f"Error {url}: {resp}"
        _LOGGER.error(error)
        raise Exception(error)

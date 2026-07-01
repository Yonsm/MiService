"""Xiaomi account authentication and token management."""

from base64 import b64encode
from hashlib import md5, sha1
from json import dumps, loads
from os import remove, path, chmod
from random import sample
from string import ascii_letters, digits
from time import time
from asyncio import get_running_loop
from urllib import parse

from typing import Optional, Callable, Awaitable

from logging import getLogger
_LOGGER = getLogger(__package__)

ACCOUNT_BASE = 'https://account.xiaomi.com'

# Xiaomi prepends this marker to JSON responses from account.xiaomi.com
_JSON_PREFIX = '&&&START&&&'

# User-Agent strings for Xiaomi API requests
UA_LOGIN = 'APP/com.xiaomi.mihome APPV/11.3.203 iosPassportSDK/4.2.50 iOS/26.3.1 MK/aVBob25lMTcsMg== DEVT/aVBob25l DEVS/aU9T BRA/QXBwbGU= L/zh_CN'

UA_OTP = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 iOS/26.3.1 MiHome/11.3.203 iPhone/iPhone17,2 DeviceId/D84D9205859533D504042022029B988E6F7DD180 UserId/8816080 APP/com.xiaomi.mihome APPV/11.3.203 Platform/iPhone Region/CN /xiaomi/miuibrowser/4.3/smartHome/ios/iPhone17,2/11.3.203 APP/com.xiaomi.mihome APPV/11.3.203 iosPassportSDK/4.2.50 iOS/26.3.1 MK/aVBob25lMTcsMg== DEVT/aVBob25l DEVS/aU9T BRA/QXBwbGU= L/zh_CN'

UA_MIIO = 'iOS-14.4-6.0.103-iPhone12,3--D7744744F7AF32F0544445285880DD63E47D9BE9-8816080-84A3F44E137B71AE-iPhone'

UA_MINA = 'MiHome/6.0.103 (com.xiaomi.mihome; build:6.0.103.1; iOS 14.4.0) Alamofire/6.0.103 MICO/iOSApp/appStore/6.0.103'


def parse_resp(raw: bytes) -> dict:
    """Strip Xiaomi's response prefix and parse the JSON body."""
    prefix = _JSON_PREFIX.encode()
    if raw.startswith(prefix):
        raw = raw[len(prefix):]
    return loads(raw) if raw else {}


def get_random(length: int) -> str:
    return ''.join(sample(ascii_letters + digits, length))


async def otp_input(otp_method: str) -> str:
    """Default OTP callback: read verification code from terminal."""
    try:
        return await get_running_loop().run_in_executor(None, input, f"Input {otp_method} Code: ")
    except EOFError:
        raise Exception("No interactive terminal for OTP input. Provide an otp_callback to MiAccount.")


class MiTokenStore:

    def __init__(self, token_path: str):
        self.token_path = token_path

    async def load_token(self) -> Optional[dict]:
        if path.isfile(self.token_path):
            try:
                def _read():
                    with open(self.token_path) as f:
                        return f.read()
                content = await get_running_loop().run_in_executor(None, _read)
                return loads(content)
            except Exception as e:
                _LOGGER.exception("Exception on load token from %s: %s", self.token_path, e)
        return None

    async def save_token(self, token: Optional[dict] = None):
        if token:
            try:
                def _write():
                    with open(self.token_path, 'w') as f:
                        f.write(dumps(token, indent=2))
                    chmod(self.token_path, 0o600)
                await get_running_loop().run_in_executor(None, _write)
            except Exception as e:
                _LOGGER.exception("Exception on save token to %s: %s", self.token_path, e)
        elif path.isfile(self.token_path):
            remove(self.token_path)


class MiAccount:
    """Manages Xiaomi account login, token storage, and session requests."""

    def __init__(self, session, username: str, password: str,
                 token_store='.mi.token',
                 otp_callback: Callable[[str], Awaitable[str]] = otp_input):
        if session is None:
            from .biohttp import ClientSession
            session = ClientSession()
        self._session = session
        self.username = username
        self.password = password
        self.token_store = MiTokenStore(token_store) if isinstance(token_store, str) else token_store
        self.otp_callback = otp_callback  # async (otp_method: str) -> str
        self.token: Optional[dict] = None
        self._login_error: Optional[str] = None

    def request(self, url: str, method: str = 'GET', **kwargs):
        return self._session.request(method, url, **kwargs)

    async def login(self, sid: str) -> bool:
        if not self.token:
            self.token = {'deviceId': get_random(16).upper()}
        try:
            resp = await self._serviceLogin(f'serviceLogin?sid={sid}&_json=true')
            if resp.get('code') != 0:
                data = {
                    '_json': 'true',
                    'qs': resp['qs'],
                    'sid': resp['sid'],
                    '_sign': resp['_sign'],
                    'callback': resp['callback'],
                    'user': self.username,
                    'hash': md5(self.password.encode()).hexdigest().upper()
                }
                resp = await self._serviceLogin('serviceLoginAuth2', data)
                if resp.get('code') != 0:
                    raise Exception(f"Login auth failed: {resp}")
                if ntf := resp.get('notificationUrl'):
                    resp = await self._verify_otp(sid, ntf)

            for key in ('userId', 'passToken', 'location', 'nonce', 'ssecurity'):
                if key not in resp:
                    raise Exception(f"Login response missing '{key}': {resp}")
            self.token['userId'] = resp['userId']
            self.token['passToken'] = resp['passToken']

            serviceToken = await self._securityTokenService(resp['location'], resp['nonce'], resp['ssecurity'])
            self.token[sid] = (resp['ssecurity'], serviceToken)
            if self.token_store:
                await self.token_store.save_token(self.token)
            return True

        except Exception as e:
            self.token = None
            self._login_error = str(e)
            if self.token_store:
                await self.token_store.save_token()
            _LOGGER.exception("Exception on login %s: %s", self.username, e)
            return False

    async def _verify_otp(self, sid: str, ntf: str) -> dict:
        """Handle OTP (SMS/email) two-factor authentication.

        Called when serviceLoginAuth2 returns a notificationUrl instead of
        a successful login. Flow (per MiIO.chls capture):

        1. GET  notificationUrl (/fe/service/identity/authStart) -> establish session
        2. GET  /identity/list?context=... -> discover methods (flag 4=phone, 8=email)
        3. GET  /identity/auth/verifyPhone?_flag=4 -> trigger OTP send
        4. POST /identity/auth/sendPhoneTicket (retry=0&icode=) -> actually send SMS
        5. await otp_callback() -> get code from user
        6. POST /identity/auth/verifyPhone (_flag=4&ticket=...&trust=false) -> submit code
        7. GET  response location URL -> set auth cookies
        8. Re-do serviceLogin -> get full auth response (code==0)
        """
        if not self.otp_callback:
            raise Exception("OTP verification required but no otp_callback provided.")

        if not ntf.startswith('http'):
            ntf = ACCOUNT_BASE + ntf

        headers = {'User-Agent': UA_OTP}
        cookies = {'deviceId': self.token['deviceId']}

        # Step 1: Open notificationUrl to establish verification session
        _LOGGER.info("OTP verification required, opening verification session...")
        async with self.request(ntf, headers=headers, cookies=cookies) as r:
            if r.status != 200:
                raise Exception(f"Failed to open OTP verification session: HTTP {r.status}")
            raw = await r.read()
            _LOGGER.debug("Opened OTP verification session: %s", raw[:200])

        # Step 2: Get available verification methods (flag 4=phone, 8=email)
        ntf_query = parse.parse_qs(parse.urlparse(ntf).query)
        context = ntf_query.get('context', [''])[0]
        sid_param = ntf_query.get('sid', [sid])[0]
        list_url = f'{ACCOUNT_BASE}/identity/list?sid={sid_param}&supportedMask=0&_locale=zh_CN&context={context}'
        async with self.request(list_url, headers=headers, cookies=cookies) as r:
            raw = await r.read()
        idata = parse_resp(raw)

        # Step 3: Determine verification method (prefer SMS)
        flag = idata.get('flag', 4)
        otp_method = 'Email' if flag == 8 else 'Phone'

        # Step 4: Trigger OTP code send
        _LOGGER.info("Triggering %s OTP verification...", otp_method)
        async with self.request(f'{ACCOUNT_BASE}/identity/auth/verify{otp_method}?_flag={flag}&_json=true', headers=headers, cookies=cookies) as r:
            raw = await r.read()
        tresp = parse_resp(raw)
        if tresp.get('code') not in (0, None):
            raise Exception(f"Failed to trigger {otp_method} OTP send: {tresp}")

        # Step 4b: For Phone, actually send the SMS via sendPhoneTicket
        if otp_method == 'Phone':
            async with self.request(
                f'{ACCOUNT_BASE}/identity/auth/sendPhoneTicket',
                method='POST', data={'retry': '0', 'icode': '', '_json': 'true'},
                headers=headers, cookies=cookies
            ) as r:
                raw = await r.read()
            sresp = parse_resp(raw)
            if sresp.get('code') not in (0, None):
                raise Exception(f"Failed to send OTP SMS: {sresp}")

        # Step 5: Ask user for OTP code via callback
        code = await self.otp_callback(otp_method)
        if not code:
            raise Exception("No OTP code provided")

        # Step 6: Submit OTP code
        _LOGGER.info("Verifying OTP code...")
        async with self.request(
            f'{ACCOUNT_BASE}/identity/auth/verify{otp_method}?_dc={int(time() * 1000)}',
            method='POST', data={'_flag': str(flag), 'ticket': code.strip(), 'trust': 'false', '_json': 'true'},
            headers=headers, cookies=cookies
        ) as r:
            raw = await r.read()
        vresp = parse_resp(raw)

        # Step 7: Resume — follow location, then re-do serviceLogin
        location = vresp.get('location')
        if not location:
            raise Exception(f"OTP verification failed, no location in response: {vresp}")

        _LOGGER.info("OTP verification accepted, completing login...")
        if not location.startswith('http'):
            location = ACCOUNT_BASE + location

        # 7a: Follow location to set auth cookies in session
        async with self.request(location, headers=headers, cookies=cookies) as r:
            await r.read()

        # 7b: Re-do serviceLogin — session now authenticated, should return code==0
        resp = await self._serviceLogin(f'serviceLogin?sid={sid}&_json=true')
        if resp.get('code') == 0:
            return resp

        raise Exception(f"OTP verification succeeded but login resume failed: {resp}")

    async def _serviceLogin(self, uri: str, data: Optional[dict] = None) -> dict:
        """Perform a service login request to the Xiaomi account API."""
        headers = {'User-Agent': UA_LOGIN}
        cookies = {'sdkVersion': '3.9', 'deviceId': self.token['deviceId']}
        if 'passToken' in self.token:
            cookies['userId'] = self.token['userId']
            cookies['passToken'] = self.token['passToken']
        url = f'{ACCOUNT_BASE}/pass/{uri}'
        async with self.request(url, 'GET' if data is None else 'POST', data=data, cookies=cookies, headers=headers) as r:
            return parse_resp(await r.read())

    async def _securityTokenService(self, location: str, nonce, ssecurity: str) -> str:
        """Exchange login credentials for a service token via the security token service."""
        nsec = f'nonce={nonce}&{ssecurity}'
        clientSign = b64encode(sha1(nsec.encode()).digest()).decode()
        async with self.request(f'{location}&clientSign={parse.quote(clientSign)}') as r:
            serviceToken = r.cookies.get('serviceToken')
            if not serviceToken:
                raise Exception(await r.text())
            return serviceToken.value

    async def mi_request(self, sid: str, url: str, data, headers: dict, relogin: bool = True) -> dict:
        if self.token is None and self.token_store is not None:
            self.token = await self.token_store.load_token()
        if (self.token and sid in self.token) or await self.login(sid):  # Ensure login
            cookies = {'userId': self.token['userId'], 'serviceToken': self.token[sid][1]}
            content = data(self.token, cookies) if callable(data) else data
            method = 'GET' if data is None else 'POST'
            async with self.request(url, method, data=content, cookies=cookies, headers=headers) as r:
                status = r.status
                if status == 200:
                    resp = await r.json(content_type=None)
                    code = resp.get('code', -1)
                    if code == 0:
                        return resp
                    if 'auth' in resp.get('message', '').lower():
                        status = 401
                else:
                    resp = await r.text()
                if status == 401 and relogin:
                    _LOGGER.warning("Auth error on request %s %s, relogin...", url, resp)
                    self.token = None  # Auth error, reset login
                    if self.token_store:
                        await self.token_store.save_token()
                    return await self.mi_request(sid, url, data, headers, False)
        else:
            resp = f"Login failed: {self._login_error or 'unknown error'}"
        raise Exception(f"Error {url}: {resp}")

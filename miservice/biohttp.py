"""Builtin async HTTP client — urllib-based, aiohttp-compatible interface.

Drop-in fallback for aiohttp when it is not installed.

Usage::

    async with ClientSession() as session:
        async with session.get(url, cookies={...}) as resp:
            data = await resp.json()
"""

from asyncio import get_running_loop
from urllib import parse, request as urlrequest
from http.cookies import SimpleCookie
from json import loads
from contextlib import asynccontextmanager


class ClientResponse:
    """aiohttp-compatible async response wrapper around urllib."""

    def __init__(self, resp, cookies):
        self._resp = resp
        self.status = getattr(resp, 'status', None) or getattr(resp, 'code', 0)
        self.cookies = cookies
        self._body = None

    async def read(self) -> bytes:
        if self._body is None:
            self._body = await get_running_loop().run_in_executor(None, self._resp.read)
        return self._body

    async def text(self, encoding='utf-8') -> str:
        return (await self.read()).decode(encoding)

    async def json(self, content_type=None) -> dict:
        return loads(await self.read())

    def close(self):
        self._resp.close()


class _CookieCapturingRedirectHandler(urlrequest.HTTPRedirectHandler):
    """Redirect handler that accumulates Set-Cookie from every hop."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._collected_cookies.extend(headers.get_all('Set-Cookie') or [])
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _do_request(url, method, kwargs, cookie_jar=None):
    """Blocking HTTP request using urllib — called in executor thread."""
    headers = dict(kwargs.get('headers') or {})
    cookies = dict(cookie_jar or {})
    cookies.update(kwargs.get('cookies') or {})
    if cookies:
        headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in cookies.items())

    data = kwargs.get('data')
    body = None
    if data is not None:
        if isinstance(data, dict):
            body = parse.urlencode(data).encode()
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        elif isinstance(data, str):
            body = data.encode()
        else:
            body = data

    req = urlrequest.Request(url, data=body, method=method, headers=headers)

    redirect_handler = _CookieCapturingRedirectHandler()
    redirect_handler._collected_cookies = []
    opener = urlrequest.build_opener(redirect_handler)

    timeout = kwargs.get('timeout', 30)

    try:
        resp = opener.open(req, timeout=timeout)
    except urlrequest.HTTPError as e:
        # HTTPError is itself a valid response object with .read(), .headers, etc.
        resp = e

    sc = SimpleCookie()
    for header in redirect_handler._collected_cookies:
        sc.load(header)
    # Guard against responses that may not expose headers (e.g. bare HTTPError)
    resp_headers = getattr(resp, 'headers', None)
    if resp_headers is not None:
        for header in resp_headers.get_all('Set-Cookie') or []:
            sc.load(header)
    return ClientResponse(resp, sc)


class ClientSession:
    """aiohttp-compatible async session backed by urllib."""

    def __init__(self):
        self._cookie_jar = {}  # host -> {name: value}, scoped per host to avoid cross-domain leakage

    def request(self, method, url, **kwargs):
        host = parse.urlparse(url).netloc

        @asynccontextmanager
        async def ctx():
            resp = await get_running_loop().run_in_executor(
                None, _do_request, url, method, kwargs, self._cookie_jar.get(host))
            # Persist cookies from the response into this host's jar only
            host_jar = self._cookie_jar.setdefault(host, {})
            for key, morsel in resp.cookies.items():
                host_jar[key] = morsel.value
            try:
                yield resp
            finally:
                resp.close()
        return ctx()

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self.request('POST', url, **kwargs)

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

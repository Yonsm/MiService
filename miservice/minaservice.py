"""MiNA (XiaoAi Speaker) service for TTS and playback control."""

from json import dumps, loads
from typing import List, Optional, Dict
from .miaccount import MiAccount, get_random, UA_MINA

from logging import getLogger
_LOGGER = getLogger(__package__)

# Devices that require the player_play_music API instead of player_play_url
_USE_PLAY_MUSIC_API = frozenset({
    'LX04', 'LX05', 'L05B', 'L05C', 'L06', 'L06A',
    'X08A', 'X10A', 'X08C', 'X08E', 'X8F', 'X4B',
    'OH2', 'OH2P', 'X6A',
})


class MiNAService:
    """Service client for MiNA API (XiaoAi smart speakers).

    Parameter names like ``deviceId`` match the Xiaomi API field names
    rather than PEP 8 snake_case, to maintain consistency with the
    external API and backward compatibility for callers.
    """

    def __init__(self, account: MiAccount):
        self.account = account
        self._device2hardware: Dict[str, str] = {}

    async def mina_request(self, uri: str, data: Optional[dict] = None) -> dict:
        requestId = 'app_ios_' + get_random(30)
        if data is not None:
            data['requestId'] = requestId
        else:
            uri += '&requestId=' + requestId
        headers = {'User-Agent': UA_MINA}
        return await self.account.mi_request('micoapi', 'https://api2.mina.mi.com' + uri, data, headers)

    async def device_list(self, master: int = 0) -> Optional[List[dict]]:
        result = await self.mina_request('/admin/v2/device_list?master=' + str(master))
        return result.get('data') if result else None

    async def _ubus_request(self, deviceId: str, method: str, path: str, message: dict) -> dict:
        """Raw ubus request returning the full response dict."""
        message = dumps(message)
        return await self.mina_request('/remote/ubus', {'deviceId': deviceId, 'message': message, 'method': method, 'path': path})

    async def ubus_request(self, deviceId: str, method: str, path: str, message: dict) -> bool:
        """ubus request returning True on success (code == 0)."""
        result = await self._ubus_request(deviceId, method, path, message)
        return result is not None and result.get('code') == 0

    async def text_to_speech(self, deviceId: str, text: str) -> bool:
        return await self.ubus_request(deviceId, 'text_to_speech', 'mibrain', {'text': text})

    async def player_set_volume(self, deviceId: str, volume) -> bool:
        return await self.ubus_request(deviceId, 'player_set_volume', 'mediaplayer', {'volume': volume, 'media': 'app_ios'})

    async def player_pause(self, deviceId: str) -> bool:
        return await self.ubus_request(deviceId, 'player_play_operation', 'mediaplayer', {'action': 'pause', 'media': 'app_ios'})

    async def player_stop(self, deviceId: str) -> bool:
        return await self.ubus_request(deviceId, 'player_play_operation', 'mediaplayer', {'action': 'stop', 'media': 'app_ios'})

    async def player_play(self, deviceId: str) -> bool:
        return await self.ubus_request(deviceId, 'player_play_operation', 'mediaplayer', {'action': 'play', 'media': 'app_ios'})

    async def player_get_status(self, deviceId: str) -> Optional[dict]:
        """Get the current playback status of a device.

        Returns the parsed status dict from the ubus ``info`` field,
        or the raw ``data`` dict if ``info`` is not present / not JSON.
        """
        result = await self._ubus_request(deviceId, 'player_get_play_status', 'mediaplayer', {'media': 'app_ios'})
        if result and result.get('code') == 0 and 'data' in result:
            data = result['data']
            # ubus responses typically wrap the actual payload in data.info (a JSON string)
            info = data.get('info')
            if isinstance(info, str):
                try:
                    return loads(info)
                except (ValueError, TypeError):
                    pass
            return data
        return None

    async def player_set_loop(self, deviceId: str, loop_type: int = 1) -> bool:
        """Set loop mode of the mediaplayer.

        loop_type: 0=single (one-track repeat), 1=list (sequential), 2=random.
        Note: this only affects devices using the ``player_play_url`` path; on
        ``player_play_music`` hardware the loop behaviour is driven by the
        ``play_behavior`` field in :meth:`play_by_music_url`.
        """
        return await self.ubus_request(deviceId, 'player_set_loop', 'mediaplayer', {'media': 'common', 'type': loop_type})

    async def play_by_url(self, deviceId: str, url: str, _type: int = 2) -> bool:
        """Play audio by URL. Automatically selects the correct API based on device hardware."""
        if deviceId not in self._device2hardware:
            await self._init_devices()
        hardware = self._device2hardware.get(deviceId)
        if hardware in _USE_PLAY_MUSIC_API:
            return await self.play_by_music_url(deviceId, url, _type)
        return await self.ubus_request(deviceId, 'player_play_url', 'mediaplayer', {'url': url, 'type': _type, 'media': 'app_ios'})

    async def play_by_music_url(self, deviceId: str, url: str, _type: int = 2,
                                audio_id: str = '1582971365183456177',
                                cp_id: str = '355454500') -> bool:
        """Play audio using the player_play_music API (required by some hardware models)."""
        _LOGGER.debug("play_by_music_url url:%s, type:%d", url, _type)
        audio_type = ''
        if _type == 1:
            # MUSIC type turns on the light ring on some speakers
            audio_type = 'MUSIC'
        music = {
            'payload': {
                'audio_type': audio_type,
                'audio_items': [
                    {
                        'item_id': {
                            'audio_id': audio_id,
                            'cp': {
                                'album_id': '-1',
                                'episode_index': 0,
                                'id': cp_id,
                                'name': 'xiaowei',
                            },
                        },
                        'stream': {'url': url},
                    }
                ],
                'list_params': {
                    'listId': '-1',
                    'loadmore_offset': 0,
                    'origin': 'xiaowei',
                    'type': 'MUSIC',
                },
            },
            'play_behavior': 'REPLACE_ALL',
        }
        return await self.ubus_request(deviceId, 'player_play_music', 'mediaplayer',
                                       {'startaudioid': audio_id, 'music': dumps(music)})

    async def get_latest_ask(self, deviceId: str) -> List[dict]:
        """Get the latest AI query results from a XiaoAi speaker.

        Returns a list of message dicts, each containing:
          - request_id: str
          - timestamp_ms: int
          - response: dict with 'answer' list
        """
        messages = []
        result = await self._ubus_request(deviceId, 'nlp_result_get', 'mibrain', {})
        if not result or result.get('code') != 0:
            return messages
        data = result.get('data', {})
        if not data or data.get('code') != 0:
            return messages
        try:
            items = loads(data.get('info', '{}')).get('result', [])
        except (ValueError, TypeError):
            return messages
        for item in items:
            if 'nlp' not in item:
                continue
            try:
                nlp = loads(item['nlp'])
                meta = nlp.get('meta', {})
                answers = nlp.get('response', {}).get('answer', [])
                msg = {
                    'request_id': meta.get('request_id', ''),
                    'timestamp_ms': int(meta.get('timestamp', 0)),
                    'response': {
                        'answer': [
                            {
                                'domain': a.get('domain', ''),
                                'action': a.get('action', ''),
                                'content': a.get('content', {}).get('to_speak', '') if isinstance(a.get('content'), dict) else a.get('content', ''),
                                'question': a.get('intention', {}).get('query', '') if isinstance(a.get('intention'), dict) else '',
                            }
                            for a in answers
                        ]
                    },
                }
                messages.append(msg)
            except (ValueError, TypeError, KeyError):
                continue
        return messages

    async def _init_devices(self, devices: Optional[List[dict]] = None):
        """Build the deviceID -> hardware mapping.

        Pass an already-fetched device list via *devices* to avoid an extra
        device_list() request when the caller has one on hand.
        """
        hardware_data = devices if devices is not None else await self.device_list()
        if hardware_data:
            for h in hardware_data:
                deviceId = h.get('deviceID', '')
                hardware = h.get('hardware', '')
                if deviceId and hardware:
                    self._device2hardware[deviceId] = hardware

    async def send_message(self, devices, devno: int, message: Optional[str] = None, volume=None) -> bool:  # -1/1/2...
        result = False
        for i in range(0, len(devices)):
            capabilities = devices[i].get('capabilities') or {}
            if devno == -1 or devno == i + 1 or capabilities.get('yunduantts'):
                _LOGGER.debug("Send to devno=%d index=%d: %s", devno, i, message or volume)
                deviceId = devices[i]['deviceID']
                result = True if volume is None else await self.player_set_volume(deviceId, volume)
                if result and message:
                    result = await self.text_to_speech(deviceId, message)
                if not result:
                    _LOGGER.error("Send failed: %s", message or volume)
                if devno != -1:
                    break
        return result
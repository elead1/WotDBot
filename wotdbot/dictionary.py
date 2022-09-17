import asyncio
from typing import Dict
import aiohttp
import datetime

class DictAPI:
    _DICT_URL = "https://od-api.oxforddictionaries.com/api/v2/entries/en-gb/"
    _DICT_APPID = "1b246251"
    _DICT_KEY = "97fe54771a751c73dda9a9a25806792a"

    _DAILY_MAX = 1000
    _daily_calls = 0
    _last_query = 0
    _call_lock = asyncio.Lock()

    async def get_definition(word: str):
        url = DictAPI._DICT_URL + word.lower()
        async with DictAPI._call_lock:
            if DictAPI._daily_calls < DictAPI._DAILY_MAX:
                DictAPI._daily_calls += 1
                DictAPI._last_query = datetime.now()
                async with aiohttp.ClientSession() as session:
                    params = {'app_id': DictAPI._DICT_APPID, 'app_key': DictAPI._DICT_KEY}
                    async with session.get(url, params=params) as resp:
                        definition = resp.json()


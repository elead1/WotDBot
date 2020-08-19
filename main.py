import os
import urllib.request
import bs4
import re
import discord
from discord.ext import commands
from discord import Embed
import asyncio
from typing import List
import json

WOTD_SERVER_CHANNELS = json.loads("servers.json")

WOTD_URL = "https://www.dictionary.com/e/word-of-the-day/"
WOTD_WORD_CLASS = "otd-item-headword__word"
WOTD_WORD_POS_CLASS = "otd-item-headword__pos"  # definition resides here
WOTD_WORD_URL_CLASS = "otd-item-headword__anchors-link"

OLD_WOTD = None
bot = commands.Bot(command_prefix="?wotd ")


class Word:
    def __init__(self, word: str = None, definition: str = None, pos: List[str] = None,
                 example: str = None, url: str = None):
        self._word = word
        self._definition = definition
        self._pos = pos
        self._example = example
        self._url = url

    def __copy__(self):
        return Word(self._word, self._definition, self._pos, self.example, self._url)

    @property
    def word(self):
        return self._word

    @word.setter
    def word(self, word):
        if self._word:
            raise RuntimeError("Cannot override word. Make a new Word.")
        self._word = word

    @property
    def definition(self):
        return self._definition

    @definition.setter
    def definition(self, definition):
        if self._definition:
            raise RuntimeError("Cannot override definition. Make a new Word.")
        self._definition = definition

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        if self._pos:
            raise RuntimeError("Cannot override word. Make a new Word.")
        self._pos = pos

    @property
    def example(self):
        return self._example

    @example.setter
    def example(self, example):
        self._example = example

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url

    def to_embed(self):
        e = Embed(title="Word of the Day")
        e.add_field(name="Word", value=self._word)
        pos_value = ", ".join(self._pos)
        e.add_field(name="Part(s) of Speech", value=pos_value)
        e.add_field(name="Definition", value=self._definition)
        e.add_field(example="Example Usage", value=self._example)
        if self._url:
            e.set_footer(text="More info [here]({}).".format(self._url))
        return e


@bot.event
async def on_ready():
    print("WotDBot has entered chat; id: {0}".format(bot.user))


async def get_wotd():
    global OLD_WOTD
    soup = None
    # Retrieve the current WotD
    with urllib.request.urlopen(WOTD_URL) as response:
        contents = response.read()
    # Parse it
    soup = bs4.BeautifulSoup(contents, 'html.parser')
    word = soup.find("div", class_=WOTD_WORD_CLASS).find("h1").contents[0]
    if word == OLD_WOTD:
        # We haven't gotten a new WOTD yet
        await asyncio.sleep(600)
        return
    OLD_WOTD = word
    pos_def_div = soup.find("div", class_=WOTD_WORD_POS_CLASS)
    pos = pos_def_div.find("span", class_="luna-pos").contents[0]
    def_ex_block = tuple(pos_dev_div.find_all("p")[-1].stripped_strings)
    last_def_part = [i for i in range(len(def_ex_block)) if ":" in def_ex_block[i]][0]
    definition = " ".join(def_ex_block[:last_def_part + 1])[:-1]
    example = " ".join(def_ex_block[last_def_part + 1:])
    url = soup.find("a", class_=WOTD_WORD_URL_CLASS)['href']
    # Format it into an Embed
    wotd_embed = Word(word, definition, [pos], example, url).to_embed()
    # Find the right channel to send it to.
    async for guild in bot.fetch_guilds():
        guild.

    pass


token = os.environ.get("WOTD_SECRET")
bot.run(token)

import os
import urllib.request
import bs4
import discord
from discord.ext import commands
from discord import Embed
import asyncio
from typing import List
import json
import threading
from time import sleep
import signal

WOTD_SERVER_CHANNELS = None
if os.path.exists("servers.json"):
    with open("servers.json") as _:
        WOTD_SERVER_CHANNELS = json.load(_)
else:
    WOTD_SERVER_CHANNELS = {}

WOTD_URL = "https://www.dictionary.com/e/word-of-the-day/"
WOTD_WORD_CLASS = "otd-item-headword__word"
WOTD_WORD_POS_CLASS = "otd-item-headword__pos"  # definition resides here
WOTD_WORD_URL_CLASS = "otd-item-headword__anchors-link"

run_threads = True
threads = []

OLD_WOTD = None
bot = commands.Bot(command_prefix="!wotd ")


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
        e.set_thumbnail(url=bot.user.avatar_url)
        e.add_field(name="Word", value=self._word)
        pos_value = ", ".join(self._pos)
        e.add_field(name="Part(s) of Speech", value=pos_value)
        e.add_field(name="Definition", value=self._definition)
        e.add_field(name="Example Usage", value=self._example)
        if self._url:
            e.add_field(name="More info...", value="..can be found [here]({}).".format(self._url))
        return e


@bot.event
async def on_ready():
    print("WotDBot has entered chat; id: {0}".format(bot.user))
    for guild in bot.guilds:
        # gather any new channels to post in
        if guild.id not in WOTD_SERVER_CHANNELS:
            # fetch default, accessible channel in server
            if type(guild.channels[0]) is discord.CategoryChannel:
                WOTD_SERVER_CHANNELS[guild.id] = guild.channels[0].channels[0].id
            else:
                WOTD_SERVER_CHANNELS[guild.id] = guild.channels[0].id
        # start posting!
        t = threading.Thread(target=wotd_loop, args=(asyncio.get_event_loop(), guild))
        t.start()
        threads.append(t)


@bot.event
async def on_disconnect():
    global run_threads
    run_threads = False
    for t in threads:
        t.join()
    with open("servers.json", "w") as _:
        json.dump(WOTD_SERVER_CHANNELS, _)


def wotd_loop(loop, guild):
    while run_threads:
        get_and_send_wotd(loop, guild)
        sleep(24 * 60 * 60)


def get_and_send_wotd(loop, guild):
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
        sleep(600)
        return
    OLD_WOTD = word
    pos_def_div = soup.find("div", class_=WOTD_WORD_POS_CLASS)
    pos = pos_def_div.find("span", class_="luna-pos").contents[0]
    def_ex_block = tuple(pos_def_div.find_all("p")[-1].stripped_strings)
    last_def_part = [i for i in range(len(def_ex_block)) if ":" in def_ex_block[i]][0]
    definition = " ".join(def_ex_block[:last_def_part + 1])[:-1]
    example = " ".join(def_ex_block[last_def_part + 1:])
    url = soup.find("a", class_=WOTD_WORD_URL_CLASS)['href']
    # Format it into an Embed
    wotd_embed = Word(word, definition, [pos], example, url).to_embed()
    wotd_embed.set_footer(text="Change the bot's channel with the `!wotd channel` command.")
    asyncio.run_coroutine_threadsafe(bot.get_channel(WOTD_SERVER_CHANNELS[guild.id]).send(embed=wotd_embed), loop)


@bot.command()
async def channel(ctx: commands.Context, chan: str):
    pass


def onexit(sig, frame):
    asyncio.run(on_disconnect())


signal.signal(signal.SIGINT, onexit)
token = os.environ.get("WOTD_SECRET")
bot.run(token)

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
import signal
import re
import sys
import pickle
import requests
import datetime


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

RANDWORD_URL = "https://random-word-api.herokuapp.com/word?"

SUPPORTED_FORMATTING = {'italic': "*{}*",
                        'bold': "**{}**"}

channel_id_fmt = re.compile(r"<#(\d+)>")


sleep_event = threading.Event()
run_thread = True
poll_thread = None

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!wotd ", intents=intents)

def EMBED_TEMPLATE():
    e = Embed(title="Word of the Day")
    e.set_thumbnail(url=bot.user.avatar)
    return e


class Word:
    def __init__(self, word: str = None, url: str = None, extras: List[str] = None):
        self._word = word
        self._url = url
        self._extras = extras

    def __copy__(self):
        return Word(self._word, self.url, self._extras)

    def __eq__(self, other):
        return other and self._word == other.word and self._url == other.url

    def __str__(self):
        return "{} [{}]: {}".format(self._word, self._url, self._extras)

    @property
    def word(self):
        return self._word

    @word.setter
    def word(self, word):
        if self._word:
            raise RuntimeError("Cannot override word. Make a new Word.")
        self._word = word

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        if self._url:
            raise RuntimeError("Cannot override URL. Make a new Word.")
        self._url = url

    @property
    def extras(self):
        return self._extras

    @extras.setter
    def extras(self, extras: List[str]):
        self._extras = extras

    def to_embed(self):
        e = EMBED_TEMPLATE()
        e.add_field(name="Word", value="[{}]({})".format(self._word, self._url))
        meaning_value = "\n".join(self._extras)
        e.add_field(name="Meaning", value=meaning_value)
        return e


if os.path.exists("lastword.pickle"):
    with open("lastword.pickle", "rb") as _:
        OLD_WOTD = pickle.load(_)
else:
    OLD_WOTD = None
print(OLD_WOTD)


@bot.event
async def on_ready():
    global poll_thread
    print("WotDBot has entered chat; id: {0}".format(bot.user))
    for guild in bot.guilds:
        # gather any new channels to post in
        if str(guild.id) not in WOTD_SERVER_CHANNELS:
            # fetch default, accessible channel in server
            if type(guild.channels[0]) is discord.CategoryChannel:
                WOTD_SERVER_CHANNELS[guild.id] = guild.channels[0].channels[0].id
            else:
                WOTD_SERVER_CHANNELS[guild.id] = guild.channels[0].id
        # start posting!
    if not poll_thread:
        poll_thread = threading.Thread(target=wotd_loop, args=(asyncio.get_event_loop(),))
        poll_thread.start()


def onexit():
    global run_thread
    run_thread = False
    sleep_event.set()
    poll_thread.join()
    with open("servers.json", "w") as _:
        json.dump(WOTD_SERVER_CHANNELS, _)
    with open("lastword.pickle", "wb") as _:
        pickle.dump(OLD_WOTD, _)
    sys.exit(0)


def get_wotd() -> Word:
    # Retrieve the current WotD
    with urllib.request.urlopen(WOTD_URL) as response:
        contents = response.read()
    # Parse it
    soup = bs4.BeautifulSoup(contents, 'html.parser')
    word = soup.find("div", class_=WOTD_WORD_CLASS).stripped_strings.__next__()
    url = soup.find("a", class_=WOTD_WORD_URL_CLASS)['href']
    pos_def_div = soup.find("div", class_=WOTD_WORD_POS_CLASS).find_all("p")
    extras = []
    for el in pos_def_div:
        formatting = "{}"
        if el.span and "luna-example" not in el.span["class"]:  # TODO: Fix parsing for example text
            decorator = set(el.span["class"]).intersection(set(SUPPORTED_FORMATTING.keys()))
            if len(decorator) > 0:
                formatting = SUPPORTED_FORMATTING[list(decorator)[0]]
        extras.append(formatting.format(el.stripped_strings.__next__()))
    # Format it into an Embed
    w = Word(word, url, extras)
    print(w)
    return w


# @bot.event
# async def on_disconnect():
#     onexit()


def wotd_loop(loop):
    global OLD_WOTD
    while run_thread:
        sleep_event.clear()
        word = get_wotd()
        if word == OLD_WOTD:
            # We haven't gotten a new WOTD yet
            sleep_event.wait(600)  # wait 10 minutes and try again
            continue
        OLD_WOTD = word
        send_coros = [send_wotd(guild, word.to_embed()) for guild in WOTD_SERVER_CHANNELS.keys()]
        asyncio.set_event_loop(loop)
        asyncio.gather(*send_coros)

def wordle_seed_loop(loop):
    global LAST_WORDLE_SEND
    while run_thread:
        if LAST_WORDLE_SEND - datetime.datetime():
            pass
        embed = get_rand_word()


def get_rand_word(as_embed=True) ->  Embed:
    with requests.get(RANDWORD_URL, params={'length': 5}) as resp:
        word = resp.json()[0]
        e = EMBED_TEMPLATE()
        e.add_field(name="Wordle Starter", value=f"{word}")
        return e


async def send_wotd(guild, wotd_embed):
    wotd_embed.set_footer(text="Change the bot's channel with the `!wotd channel` command.")
    await bot.get_channel(WOTD_SERVER_CHANNELS[guild]).send(embed=wotd_embed)


@bot.command()
async def channel(ctx: commands.Context, chan: str):
    chan_id = int(channel_id_fmt.match(chan).group(1))
    WOTD_SERVER_CHANNELS[ctx.guild.id] = chan_id
    await ctx.send("Changed channel to {}".format(chan))

@bot.command()
async def define(ctx: commands.Context, query: str):
    definition = resp.json()
    embed = parse_def(definition)
    ctx.send(embed=embed)


def exit_handler(sig, frame):
    print("Exiting!")
    onexit()


signal.signal(signal.SIGINT, exit_handler)
if os.path.exists("../secrets"):
    with open("../secrets") as _:
        secrets = json.load(_)
token = secrets["WOTD"]
bot.run(token)

import os
from socketserver import ThreadingUnixStreamServer
from tkinter import LAST
import bs4
import discord
from discord.ext import commands
from discord import Embed
import asyncio
from typing import List
import json
import signal
import re
import sys
import requests
import datetime
from wotdbot import word, utils

settings = None 
if os.path.exists("settings.json"):
    with open("settings.json") as _:
        settings = json.load(_)

if settings:
    WOTD_SERVER_CHANNELS = {k: settings["servers"][k]["channel"] for k in settings["servers"]}
else:
    WOTD_SERVER_CHANNELS = {}

try:
    OLD_WOTD = word.Word.fromJson(json.loads(settings["prev_wotd"]))
except KeyError:
    OLD_WOTD = None
print(OLD_WOTD)

try:
    rw = datetime.datetime.fromtimestamp(settings["last_wordle"])
    LAST_RANDWORD = datetime.datetime(rw.year, rw.month, rw.day, 0, 0, 0, 0, datetime.timezone.utc)
except KeyError:
    today = datetime.datetime.now()
    yesterday = today + datetime.timedelta(days=-1)
    LAST_RANDWORD = datetime.datetime(yesterday.year, yesterday.month, yesterday.date, 0, 0, 0, 0, datetime.timezone.utc)
print(LAST_RANDWORD)

WOTD_URL = "https://www.dictionary.com/e/word-of-the-day/"
WOTD_WORD_CLASS = "otd-item-headword__word"
WOTD_WORD_POS_CLASS = "otd-item-headword__pos"  # definition resides here
WOTD_WORD_URL_CLASS = "otd-item-headword__anchors-link"

RANDWORD_URL = "https://random-word-api.herokuapp.com/word?"

SUPPORTED_FORMATTING = {'italic': "*{}*",
                        'bold': "**{}**"}

channel_id_fmt = re.compile(r"<#(\d+)>")


tasks = set()

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!wotd ", intents=intents)


def find_store_accessible_channel(guild) -> int:
    # fetch default, accessible channel in server
    if type(guild.channels[0]) is discord.CategoryChannel:
        WOTD_SERVER_CHANNELS[guild.id] = guild.channels[0].channels[0].id
    else:
        WOTD_SERVER_CHANNELS[guild.id] = guild.channels[0].id
    settings["servers"][guild.id] = {"channel": WOTD_SERVER_CHANNELS[guild.id]}

@bot.event
async def on_ready():
    print("WotDBot has entered chat; id: {0}".format(bot.user))
    for guild in bot.guilds:
        # gather any new channels to post in
        if str(guild.id) not in WOTD_SERVER_CHANNELS:
            find_store_accessible_channel(guild)
    # create a coroutine per server
    for s in WOTD_SERVER_CHANNELS:
        configure_task(send_wotd(s), f"wotd-{guild.id}")
        if settings["servers"][s]["send_wordle"]:
            configure_task(send_wordle_seed(s), f"wordle-{guild.id}")


@bot.event
async def on_guild_join(guild):
    find_store_accessible_channel(guild)
    print(f"Joined server: {guild.id}, channel: {WOTD_SERVER_CHANNELS[guild.id]}")
    configure_task(send_wotd(guild), f"wotd-{guild.id}")
    await bot.get_channel(WOTD_SERVER_CHANNELS[guild.id]).send("`!wotd help` for command info.")


@bot.event
async def on_guild_remove(guild):
    del WOTD_SERVER_CHANNELS[guild.id]
    del settings["servers"][guild.id]
    for t in tasks:
        if f"{guild.id}" in t.get_name():
            t.cancel()


def configure_task(func, name):
    task = asyncio.create_task(func, name=name)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def onexit():
    with open("settings.json", "w") as _:
        json.dump(settings, _)
    sys.exit(0)


async def get_wotd() -> word.Word:
    # Retrieve the current WotD
    with requests.get(WOTD_URL) as response:
        contents = response.content
    # Parse it
    soup = bs4.BeautifulSoup(contents, 'html.parser')
    w = soup.find("div", class_=WOTD_WORD_CLASS).stripped_strings.__next__()
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
    w = word.Word(w, url, extras)
    # We haven't gotten a new WotD yet
    if w == OLD_WOTD:
        await asyncio.sleep(600) # wait 10 minutes and try again
        return await get_wotd()
    else:
        OLD_WOTD = w
        settings["prev_wotd"] = OLD_WOTD.toJson()
        return w


async def get_rand_word() -> Embed:
    now = datetime.datetime.now(datetime.timezone.utc)
    # if it has been more than 1 day since last word was sent, and it is past midnight UTC, get a new word
    if (now - LAST_RANDWORD).total_seconds > (24 * 60 * 60) and (now.hour, now.minute, now.second) > (0, 0, 0):
        with requests.get(RANDWORD_URL, params={'length': 5}) as resp:
            LAST_RANDWORD = now
            settings["last_wordle"] = now.timestamp()
            w = resp.json()[0]
            e = utils.EMBED_TEMPLATE(bot)
            e.add_field(name="Wordle Starter", value=f"{w}")
            return e
    else:
        await asyncio.sleep(600)  # wait 10 minutes and try again
        return await get_rand_word()


async def send_wotd(guild):
    if settings["servers"][guild]["send_wordle"]:
        w = await get_wotd()
        wotd_embed = w.to_embed(bot)
        wotd_embed.set_footer(text="Change the bot's channel with the `!wotd channel` command.")
        await bot.get_channel(WOTD_SERVER_CHANNELS[guild]).send(embed=wotd_embed)
        t = asyncio.create_task(send_wotd(guild))
        tasks.add(t)


async def send_wordle_seed(guild):
    embed = await get_rand_word()
    embed.set_footer(text="Change the bot's channel with the `!wotd channel` command.")
    await bot.get_channel(WOTD_SERVER_CHANNELS[guild]).send(embed=embed)
    t = asyncio.create_task(send_wotd(guild))
    tasks.add(t)


@bot.command()
async def channel(ctx: commands.Context, chan: str):
    chan_id = int(channel_id_fmt.match(chan).group(1))
    WOTD_SERVER_CHANNELS[ctx.guild.id] = chan_id
    settings["servers"][ctx.guild.id]["channel"] = chan_id
    await ctx.send("Changed channel to {}".format(chan))


@bot.command()
async def wordle(ctx: commands.Context):
    settings["servers"][ctx.guild.id]["send_wordle"] = True
    configure_task(send_wordle_seed(ctx.guild, f"wordle-{ctx.guild.id}"))
    await ctx.send("WotDBot will post daily Wordle starters. Use command `!wotd nowordle` to disable.")


@bot.command()
async def nowordle(ctx: commands.Context):
    settings["servers"][ctx.guild.id]["send_wordle"] = False
    for t in tasks:
        if t.get_name() == f"wordle-{ctx.guild.id}":
            t.cancel()
    await ctx.send("WotDBot will no longer post daily Wordle starters. Use command `!wotd wordle` to re-enable.")

# @bot.command()
# async def define(ctx: commands.Context, query: str):
#     definition = resp.json()
#     embed = parse_def(definition)
#     ctx.send(embed=embed)


# @bot.event
# async def on_disconnect():
#     onexit()


def exit_handler(sig, frame):
    print("Exiting!")
    onexit()


signal.signal(signal.SIGINT, exit_handler)
if os.path.exists("../secrets"):
    with open("../secrets") as _:
        secrets = json.load(_)
token = secrets["WOTD"]
bot.run(token)

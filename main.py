import os
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
import word

settings = None 
if os.path.exists("settings.json"):
    with open("settings.json") as _:
        settings = json.load(_)

if settings:
    WOTD_SERVER_CHANNELS = {k: settings["servers"][k]["channel"] for k in settings["servers"]}
else:
    WOTD_SERVER_CHANNELS = {}

try:
    OLD_WOTD = settings["prev_wotd"]
except KeyError:
    OLD_WOTD = None
print(OLD_WOTD)


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

def EMBED_TEMPLATE():
    e = Embed(title="Word of the Day")
    e.set_thumbnail(url=bot.user.avatar)
    return e

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
            settings["servers"][guild.id] = {"channel": WOTD_SERVER_CHANNELS[guild.id]}
    # create a coroutine per server
    for s in WOTD_SERVER_CHANNELS:
        task = asyncio.create_task(send_wotd(s))
        tasks.add(task)
        task.add_done_callback(tasks.discard)


def onexit():
    with open("settings.json", "w") as _:
        json.dump(settings, _)
    sys.exit(0)


async def get_wotd() -> word.Word:
    global OLD_WOTD
    # Retrieve the current WotD
    with requests.get(WOTD_URL) as response:
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
    w = word.Word(word, url, extras)
    # We haven't gotten a new WotD yet
    if w == OLD_WOTD:
        await asyncio.sleep(600) # wait 10 minutes and try again
        return await get_wotd()
    else:
        OLD_WOTD = w
        settings["prev_wotd"] = OLD_WOTD
        return w


# @bot.event
# async def on_disconnect():
#     onexit()


# def wotd_loop(loop):
#     global OLD_WOTD
#     while run_thread:
#         sleep_event.clear()
#         word = get_wotd()
#         if word == OLD_WOTD:
#             # We haven't gotten a new WOTD yet
#             sleep_event.wait(600)  # wait 10 minutes and try again
#             continue
#         OLD_WOTD = word
#         send_coros = [send_wotd(guild, word.to_embed()) for guild in WOTD_SERVER_CHANNELS.keys()]
#         asyncio.set_event_loop(loop)
#         asyncio.gather(*send_coros)

# def wordle_seed_loop(loop):
#     global LAST_WORDLE_SEND
#     while run_thread:
#         if LAST_WORDLE_SEND - datetime.datetime():
#             pass
#         embed = get_rand_word()


def get_rand_word(as_embed=True) ->  Embed:
    with requests.get(RANDWORD_URL, params={'length': 5}) as resp:
        word = resp.json()[0]
        e = EMBED_TEMPLATE()
        e.add_field(name="Wordle Starter", value=f"{word}")
        return e


async def send_wotd(guild):
    global tasks
    word = await get_wotd()
    wotd_embed = word.to_embed()
    wotd_embed.set_footer(text="Change the bot's channel with the `!wotd channel` command.")
    await bot.get_channel(WOTD_SERVER_CHANNELS[guild]).send(embed=wotd_embed)
    t = asyncio.create_task(send_wotd(guild))
    tasks.add(t)


@bot.command()
async def channel(ctx: commands.Context, chan: str):
    chan_id = int(channel_id_fmt.match(chan).group(1))
    WOTD_SERVER_CHANNELS[ctx.guild.id] = chan_id
    settings["servers"][ctx.guild.id]["channel"] = chan_id
    await ctx.send("Changed channel to {}".format(chan))

# @bot.command()
# async def define(ctx: commands.Context, query: str):
#     definition = resp.json()
#     embed = parse_def(definition)
#     ctx.send(embed=embed)


def exit_handler(sig, frame):
    print("Exiting!")
    onexit()


signal.signal(signal.SIGINT, exit_handler)
if os.path.exists("../secrets"):
    with open("../secrets") as _:
        secrets = json.load(_)
# token = secrets["WOTD"]
token = 
bot.run(token)

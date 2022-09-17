import discord

def EMBED_TEMPLATE(bot):
    e = discord.Embed(title="Word of the Day")
    e.set_thumbnail(url=bot.user.avatar)
    return e


import discord
from discord.ext import commands
from .utils import checks


class SpellIt:
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        content = message.content
        if message.author.bot:
            return
        user = message.author.name
        if 'bb' in content:
            meme_ref = 'bb'
        elif 'pp' in content:
            meme_ref = 'pp'
        else:
            return
        await self.bot.send_message(message.channel, "{} you said {}".format(user, meme_ref))


def setup(bot):
    n = SpellIt(bot)
    bot.add_listener(n.on_message, "on_message")
    bot.add_cog(n)
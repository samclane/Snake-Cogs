import discord
from discord.ext import commands
from .utils import checks
import time
from PIL import Image


class FidgetSpinner:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=False, no_pm=True)
    async def spin(self):
        im = Image.open("data\\fidget-spinner\\spinner.png")
        txt = self.pixelize(im)
        msg = await self.bot.say(txt)
        for deg in range(0, 360, 90):
            im = im.rotate(deg)
            txt = self.pixelize(im)
            await self.bot.edit_message(msg, txt)
            time.sleep(.5)

    def pixelize(self, im):
        msg = "```\n"
        size = im.size
        for rownum in range(size[1]):
            line = []
            for colnum in range(size[0]):
                if im.getpixel((colnum, rownum)):
                    line.append(' '),
                else:
                    line.append('#'),
            msg += ''.join(line) + '\n'
        msg += '```'
        return msg


def setup(bot):
    n = FidgetSpinner(bot)
    bot.add_cog(n)

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
        im = Image.open("data/fidget-spinner/spinner.png")
        txt = self.pixelize(im)
        msg = await self.bot.say(txt)
        for deg in range(0, 720, 90):
            im = im.rotate(deg)
            txt = self.pixelize(im)
            t = time.time()
            await self.bot.edit_message(msg, txt)
            time.sleep(max(.5 - (time.time() - t), 0))  # wait remainder of .5 seconds

    @staticmethod
    def pixelize(im):
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

import time
from io import BytesIO

import requests
from PIL import Image
from discord.ext import commands


class FidgetSpinner:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=False, no_pm=True)
    async def spin(self, url=None):
        if url is not None:
            response = requests.get(url)
            im = Image.open(BytesIO(response.content))
            im = self.resize_and_binarize(im)
        else:
            im = Image.open("data/fidget-spinner/spinner.png")
        txt = self.pixelize(im)
        msg = await self.bot.say(txt)
        for deg in range(0, 720, 90):
            im = im.rotate(deg)
            txt = self.pixelize(im)
            t = time.time()
            await self.bot.edit_message(msg, txt)
            time.sleep(max(.5 - (time.time() - t), 0))  # wait remainder of .5 seconds

    @commands.group(pass_context=False, no_pm=True)
    async def spinHD(self, url=None):
        if url is not None:
            response = requests.get(url)
            im = Image.open(BytesIO(response.content))
            im = self.resize_and_8b(im)
        else:
            im = Image.open("data/fidget-spinner/spinner.png")
        txt = self.pixelize2(im)
        msg = await self.bot.say(txt)
        for deg in range(0, 720, 90):
            im = im.rotate(deg)
            txt = self.pixelize2(im)
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

    @staticmethod
    def pixelize2(im):
        sp = u" "
        lt = u"░"
        md = u"▒"
        dk = u"▓"
        msg = "```\n"
        size = im.size
        for rownum in range(size[1]):
            line = []
            for colnum in range(size[0]):
                if 255 >= im.getpixel((colnum, rownum)) >= 3 * (255 // 4):
                    line.append(sp),
                elif 3 * (255 // 4) >= im.getpixel((colnum, rownum)) >= 2 * (255 // 4):
                    line.append(lt),
                elif 2 * (255 // 4) >= im.getpixel((colnum, rownum)) >= (255 // 4):
                    line.append(md),
                else:
                    line.append(dk)
            msg += ''.join(line) + '\n'
        msg += '```'
        return msg

    @staticmethod
    def resize_and_binarize(im: Image):
        im = im.convert('1')
        im = im.resize((25, 25))
        return im

    @staticmethod
    def resize_and_8b(im: Image):
        im = im.convert('L')
        im = im.resize((25, 25))
        return im


def setup(bot):
    n = FidgetSpinner(bot)
    bot.add_cog(n)

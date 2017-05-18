import discord
from discord.ext import commands
from .utils import checks
import time

SPINNER_A = "  |  \n" \
          " / \\"


SPINNER_B = "  /\n" \
            "- \n" \
            "  \\"

SPINNER_C = " \\ /\n" \
            "  |"

SPINNER_D = "  \\\n" \
            "    -\n" \
            "  /"

class FidgetSpinner:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=False, no_pm=True)
    async def spin(self):
        """Change DamnDog Settings"""
        msg = await self.bot.say(SPINNER_A)
        for state in [SPINNER_B, SPINNER_C, SPINNER_D, SPINNER_A]:
            time.sleep(.5)
            msg = await self.bot.edit_message(msg, state)

def setup(bot):
    n = FidgetSpinner(bot)
    bot.add_cog(n)



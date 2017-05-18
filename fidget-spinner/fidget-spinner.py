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
        embed = discord.Embed()
        embed.add_field(name="Spinner", value=SPINNER_A)
        msg = await self.bot.say(embed=embed)
        for state in [SPINNER_B, SPINNER_C, SPINNER_D, SPINNER_A]:
            time.sleep(.5)
            embed = discord.Embed()
            embed.add_field(name="Spinner", value=state)
            msg = await self.bot.edit_message(msg, embed=embed)


def setup(bot):
    n = FidgetSpinner(bot)
    bot.add_cog(n)

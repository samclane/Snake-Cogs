from discord.ext import commands
from .utils import checks
import socket


class IpHelper:
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def get_ip_address():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=False, no_pm=False, name='iphelp')
    async def iphelp(self):
        await self.bot.whisper(self.get_ip_address())


def setup(bot):
    n = IpHelper(bot)
    bot.add_cog(n)

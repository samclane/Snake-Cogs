import discord
import sys
from socket import *

class NetworkTool:
    def __init__(self, bot):
        self.bot = bot
        self.sock = self.redirectOut()

    def redirectOut(self, port=50008, host='localhost'):
        """
        connect caller's standard output stream to a socket for GUI to listen
        start caller after listener started, else connect fails before accept
        """
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(('192.168.1.69', port))
        sock.connect(('192.168.1.69', port))  # caller operates in client mode
        file = sock.makefile('w', buffering=None)  # file interface: text, buffered
        sys.stdout = file  # make prints go to sock.send
        return sock


def setup(bot):
    n = NetworkTool(bot)
    bot.add_cog(n)

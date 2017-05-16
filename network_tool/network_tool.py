import discord
import sys
from socket import *


class NetworkTool:
    def __init__(self, bot):
        self.bot = bot

        serversocket = MySocket()
        serversocket.bind(("192.168.1.69", 50008))
        serversocket.listen(1)
        conn, addr = serversocket.accept1()
        sys.stdout = conn
        sys.stdin = conn
        sys.stderr = conn


class MySocket(socket):
    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _sock=None):
        socket.__init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _sock=None)

    def write(self, text):
        return self.send(text)

    def readlines(self):
        return self.recv(2048)

    def read(self):
        return self.recv(1024)

    def accept1(self):
        conn, addr = self.accept()
        return (MySocket(_sock=conn), addr)


def setup(bot):
    n = NetworkTool(bot)
    bot.add_cog(n)

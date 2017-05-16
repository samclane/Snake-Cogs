import discord
import sys
import socket
import select

# force update

class NetworkTool:
    def __init__(self, bot):
        self.bot = bot
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('', 8888))
        self.server_socket.listen(5)

        file = self.server_socket.makefile('w', buffering=None)  # file interface: text, buffered
        sys.stdout = file



    async def service_port(self):
        read_list = [self.server_socket]
        while True:
            readable, writable, errored = select.select(read_list, [], [])
            for s in readable:
                if s is self.server_socket:
                    client_socket, address = self.server_socket.accept()
                    read_list.append(client_socket)
                    print("Connection from ", address)
                else:
                    data = s.recv(1024)
                    if data:
                        s.send(data)
                    else:
                        s.close()
                        read_list.remove(s)


def setup(bot):
    n = NetworkTool(bot)
    bot.add_cog(n)

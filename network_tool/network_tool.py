from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket


# force update

class NetworkTool:
    def __init__(self, bot):
        self.bot = bot
        self.websocket = SimpleChat(bot)


def setup(bot):
    n = NetworkTool(bot)
    bot.add_cog(n)


clients = []
class SimpleChat(WebSocket):
    def __init__(self, bot):
        super(self, SimpleChat)
        self.bot = bot
        self.data = self.bot.__dict__

    def handleMessage(self):
       for client in clients:
          if client != self:
             client.sendMessage(self.address[0] + u' - ' + self.data)

    def handleConnected(self):
       print(self.address, 'connected')
       for client in clients:
          client.sendMessage(self.address[0] + u' - connected')
       clients.append(self)

    def handleClose(self):
       clients.remove(self)
       print(self.address, 'closed')
       for client in clients:
          client.sendMessage(self.address[0] + u' - disconnected')

server = SimpleWebSocketServer('localhost', 8000, SimpleChat)
server.serveforever()
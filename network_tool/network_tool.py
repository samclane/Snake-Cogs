import asyncio
import websockets
# force update

class NetworkTool:

    def __init__(self, bot):
        self.bot = bot

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        print("< {}".format(msg))
        if msg == "hello":
            await websocket.send(self.bot.__dict__)
        print("> {}".format(self.bot.__dict__))



def setup(bot):
    n = NetworkTool(bot)

    asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8768))

    bot.add_cog(n)


import asyncio
import websockets
# force update

class NetworkTool:

    def __init__(self, bot):
        self.bot = bot

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":
            await websocket.send("hello")
            print("> {}".format("hello"))
        elif msg == "counter":
            await websocket.send("{}".format(str(self.bot.counter)))
            print("> {}".format("{}".format(str(self.bot.counter))))



def setup(bot):
    n = NetworkTool(bot)

    asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8774))

    bot.add_cog(n)


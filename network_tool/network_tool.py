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
            await websocket.send("hello")
            print("> {}".format("hello"))
        elif msg == "counter":
            await websocket.send(self.bot.counter)
            print("> {}".format(self.bot.counter))



def setup(bot):
    n = NetworkTool(bot)

    asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8771))

    bot.add_cog(n)


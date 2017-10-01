import asyncio
import websockets
# force update

class NetworkTool:

    def __init__(self, bot):
        self.bot = bot

async def hello(websocket, path):
    name = await websocket.recv()
    print("< {}".format(name))

    greeting = "Hello {}!".format(name)
    await websocket.send(greeting)
    print("> {}".format(greeting))


def setup(bot):
    n = NetworkTool(bot)

    #asyncio.get_event_loop().run_until_complete(websockets.serve(hello, 'localhost', 8766))
    asyncio.run_coroutine_threadsafe(websockets.serve(hello, 'localhost', 8766), asyncio.get_event_loop())
    bot.add_cog(n)


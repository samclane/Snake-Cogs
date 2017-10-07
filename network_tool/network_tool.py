import asyncio

import jsonpickle
import websockets


class NetworkTool:
    def __init__(self, bot):
        self.bot = bot

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":  # first contact
            frozen = jsonpickle.encode(self.bot)
            await websocket.send(frozen)
            print(frozen)

#test
def setup(bot):
    n = NetworkTool(bot)

    try:
        asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8784))
    except RuntimeError:
        pass

    bot.add_cog(n)

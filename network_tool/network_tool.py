import asyncio
import websockets
import json


def json_default(value):
    try:
        return value.__dict__
    except AttributeError:
        return None


class NetworkTool:
    def __init__(self, bot):
        self.bot = bot

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":
            await websocket.send("hello")
            print("> {}".format("hello"))
        elif msg == "bot":
            await websocket.send(json.dumps(self.bot.__dict__))
            print("> {}".format(json.dumps(self.bot.__dict__)))


# test
def setup(bot):
    n = NetworkTool(bot)

    try:
        asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8778))
    except RuntimeError:
        pass

    bot.add_cog(n)

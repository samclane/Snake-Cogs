import asyncio
import websockets
import json

from datetime import date, datetime

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

class Object:
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)

class NetworkTool:
    def __init__(self, bot):
        self.bot = bot

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":
            await websocket.send("hello")
            print("> {}".format("hello"))
        elif msg == "bot":
            await websocket.send(json.dumps(self.bot.__dict__, default=lambda o: o.toJSON()))
            print("> {}".format(json.dumps(self.bot.__dict__, default=lambda o: o.toJSON())))


# test
def setup(bot):
    n = NetworkTool(bot)

    try:
        asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8781))
    except RuntimeError:
        pass

    bot.add_cog(n)

import asyncio
import websockets
# force update

class NetworkTool:

    def __init__(self, bot):
        self.bot = bot


    async def hello(self, websocket, path):
        name = await websocket.recv()
        print("< {}".format(name))

        greeting = "Hello {} {}!".format(name, self.bot.__dict__)
        await websocket.send(greeting)
        print("> {}".format(greeting))



def setup(bot):
    n = NetworkTool(bot)

    asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8768))

    bot.add_cog(n)


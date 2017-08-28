import asyncio
import websockets
# force update

class NetworkTool:
    def __init__(self, bot):
        self.bot = bot
        self.start_server = websockets.serve(hello, 'localhost', 8765)


    async def hello(websocket, path):
        name = await websocket.recv()
        print("< {}".format(name))

        greeting = "Hello {}!".format(name)
        await websocket.send(greeting)
        print("> {}".format(greeting))



def setup(bot):
    n = NetworkTool(bot)

    asyncio.get_event_loop().run_until_complete(n.start_server)
    asyncio.get_event_loop().run_forever()
    
    bot.add_cog(n)


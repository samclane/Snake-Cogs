from redbot.core import commands, bot

import jsonpickle

# Todo: Build "Bot" Dummp class to send to GUI
class NetworkTool(commands.Cog):
    def __init__(self, bot: bot.RedBase):
        self.bot = bot

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":  # first contact
            frozen = jsonpickle.encode(self.bot)
            await websocket.send(frozen)
            print(frozen)

from redbot.core import commands
from redbot.core import bot as r_bot

import json

class NetworkTool(commands.Cog):
    def __init__(self, bot: r_bot.RedBase):
        self.bot = bot

    def build_bot_json(self):
        return {
            "connection": {
                "user": {
                    "name": str(self.bot)
                },
                "_servers": {str(s): str(s) for s in self.bot.description}
            },
            "cogs": [type(c).__name__ for c in self.bot.cogs.values()],
            "commands": {str(c): str(c) for c in self.bot.commands},
            "settings": {
                "bot_settings": {
                    "PREFIXES": {"0": str(self.bot.command_prefix)},
                    "default": {
                        "ADMIN_ROLE": str(self.bot.owner_id)
                    }
                }
            },
            "_is_logged_in": {
                "_value": str(self.bot.uptime)
            }
        }

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":  # first contact
            bot_json = json.dumps(self.build_bot_json())
            await websocket.send(bot_json)
            print(json.dumps(self.build_bot_json()))

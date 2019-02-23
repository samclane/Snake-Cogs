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
                "_servers": [str(g) for g in self.bot.guilds]
            },
            "cogs": [type(c).__name__ for c in self.bot.cogs.values()],
            "commands": {str(c): c.help for c in self.bot.commands},
            "settings": {
                "bot_settings": {
                    "PREFIXES": {"0": str("TODO")},
                    "default": {
                        "ADMIN_ROLE": str("TODO: Remove this"),
                        "MOD_ROLE": str("TODO: Remove this")
                    }
                }
            },
            "_is_logged_in": {
                "_value": str("TODO: Remove this")
            }
        }

    async def hello(self, websocket, path):
        msg = await websocket.recv()
        if msg == "hello":  # first contact
            bot_json = json.dumps(self.build_bot_json())
            await websocket.send(bot_json)
            print(json.dumps(self.build_bot_json()))

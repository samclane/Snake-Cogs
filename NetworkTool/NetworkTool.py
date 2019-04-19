import json
import logging

from redbot.core import commands
from redbot.core.bot import Red

LOG = logging.getLogger("red.NetworkTool")


class NetworkTool(commands.Cog):
    def __init__(self, bot: Red.RedBase):
        super().__init__()
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
            LOG.info(json.dumps(self.build_bot_json()))

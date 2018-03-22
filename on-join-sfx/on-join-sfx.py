from .sfx import Sfx

import discord
import os
from cogs.utils.dataIO import dataIO


class OnJoin:

    def __init__(self, bot):
        self.bot = bot
        self.sfx = Sfx(self.bot)

    async def voice_state_update(self, before: discord.Member, after: discord.Member):
        bserver = before.server
        aserver = after.server

        bvchan = before.voice.voice_channel
        avchan = after.voice.voice_channel

        if before.bot or after.bot:
            return

        if bvchan != avchan:
            # went from no channel to a channel
            if (bvchan is None and avchan is not None):
                # came online
                text = "{} has joined the channel".format(after.display_name)
                channel = avchan
                server = aserver
            elif (bvchan is not None and avchan is None):
                # went offline
                text = "{} has left the channel".format(before.display_name)
                channel = bvchan
                server = bserver
            else:
                return
            self.sfx.enqueue_tts(channel, text)



def check_folders():
    if not os.path.exists("data/on_join"):
        print("Creating data/on_join folder...")
        os.makedirs("data/on_join")


def check_files():
    f = "data/on_join/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default on_join settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = OnJoin(bot)
    bot.add_listener(n.voice_state_update, "on_voice_state_update")
    bot.add_cog(n)
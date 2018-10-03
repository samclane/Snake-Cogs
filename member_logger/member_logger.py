import datetime
import os

import discord
import pandas
from cogs.utils.dataIO import dataIO


class MemberLogger:
    """ Gathers information on when users interact with each other. Can be used for later statistical analysis """

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.settings_path = "data/member_logger/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

        # Ensure path is set. Use default path if not.
        if "path" not in self.settings.keys():
            self.settings["datapath"] = "data/member_logger/data.csv"

        dataIO.save_json("data/on_join/settings.json", self.settings)

        # Make the datafile if it does exist.
        if not os.path.exists(self.settings["datapath"]):
            with open(self.settings["datapath"], "a"):
                os.utime(self.settings["datapath"], None)
                self.data = pandas.DataFrame({"datetime": [], "member": [], "present": []})
                self.data.to_csv(self.settings["datapath"])

        self.data = pandas.read_csv(self.settings["datapath"])

    async def on_message_(self, message: discord.Message):
        if message.author.bot:
            return
        entry = pandas.Series(
            {"datetime": datetime.datetime.now(), "member": message.author.id,
             "present": [m.id for m in message.mentions if not m.bot and m.id != message.author.id]},
            name=datetime.datetime.now())
        self.data = self.data.append(entry)
        self.data.to_csv(self.settings["datapath"])

    async def on_voice_state_update_(self, before, after: discord.Member):
        if before.bot or after.bot:
            return

        bvchan = before.voice.voice_channel
        avchan = after.voice.voice_channel

        if bvchan != avchan:
            # went from no channel to a channel
            if bvchan is None and avchan is not None:
                # came online
                entry = pandas.Series(
                    {"datetime": datetime.datetime.now(), "member": after.id,
                     "present": [m.id for m in avchan.voice_members if not m.bot and m.id != after.id]},
                    name=datetime.datetime.now())
                self.data = self.data.append(entry)
                self.data.to_csv(self.settings["datapath"])


def check_folders():
    if not os.path.exists("data/member_logger"):
        print("Creating data/member_logger folder...")
        os.makedirs("data/member_logger")


def check_files():
    f = "data/member_logger/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default member_logger settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = MemberLogger(bot)
    bot.add_listener(n.on_message_, "on_message")
    bot.add_listener(n.on_voice_state_update_, "on_voice_state_update")
    bot.add_cog(n)

import os
import time
from ast import literal_eval
import asyncio

import discord
from discord.ext import commands
import pandas
from cogs.utils.dataIO import dataIO
from sqlalchemy import create_engine

DB_UPDATE_INTERVAL = 60*30  # Every 30 minutes


class MemberLogger:
    """ Gathers information on when users interact with each other. Can be used for later statistical analysis """

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/member_logger/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

        # Ensure path is set. Use default path if not.
        if "datapath" not in self.settings.keys():
            self.settings["datapath"] = "data/member_logger/data.csv"
        if "namepath" not in self.settings.keys():
            self.settings["namepath"] = "data/member_logger/names.csv"
        if "database" not in self.settings.keys():
            self.settings["database"] = ""

        dataIO.save_json("data/member_logger/settings.json", self.settings)

        # Make the datafile if it does exist.
        if not os.path.exists(self.settings["datapath"]):
            with open(self.settings["datapath"], "a"):
                os.utime(self.settings["datapath"], None)
                self.data = pandas.DataFrame({"member": [], "present": []})
                self.data.index.name = "timestamp"
                self.data.to_csv(self.settings["datapath"])

        if not os.path.exists(self.settings["namepath"]):
            with open(self.settings["namepath"], "a"):
                os.utime(self.settings["namepath"], None)
                self.names = pandas.DataFrame({"member": [], "username": []})
                self.names.index.name = "index"
                self.names.to_csv(self.settings["namepath"])

        self.data = pandas.read_csv(self.settings["datapath"], index_col=0)
        self.data['present'] = self.data['present'].apply(literal_eval)
        self.names = pandas.read_csv(self.settings["namepath"], index_col=0)

        self.engine = None
        self.task = None
        if self.settings["database"]:
            print("Database info found...")
            self.engine = create_engine(self.settings["database"])
            self.task = self.bot.loop.create_task(self.update_database())

    def update_data(self, entry):
        self.data = self.data.append(entry)
        self.data.to_csv(self.settings["datapath"])

    def update_names(self, entry):
        self.names = self.names.append(entry, ignore_index=True)
        self.names.to_csv(self.settings["namepath"])

    async def update_database(self):
        while True:
            print("Updating database at {}".format(int(time.time())))
            self.data.to_sql('member_data', self.engine, if_exists='replace')
            self.names.to_sql('member_names', self.engine, if_exists='replace')
            print("Done updating database...")
            await asyncio.sleep(DB_UPDATE_INTERVAL)

    def __unload(self):
        if self.task:
            self.task.cancel()

    async def on_message_(self, message):
        if message.author.bot or not message.mentions or message.mention_everyone:
            return
        entry = pandas.Series(
            {"member": message.author.id,
             "present": [m.id for m in message.mentions if not m.bot and m.id != message.author.id]},
            name=int(time.time()))
        self.update_data(entry)
        if message.author.id not in self.names["member"].apply(str).values:
            self.update_names(pandas.Series({"member": message.author.id, "username": message.author.name}))

    async def on_voice_state_update_(self, before, after):
        if before.bot or after.bot:
            return

        bvchan = before.voice.voice_channel
        avchan = after.voice.voice_channel

        if bvchan != avchan:
            # went from no channel to a channel
            if bvchan is None and avchan is not None:
                # came online
                entry = pandas.Series(
                    {"member": after.id,
                     "present": [m.id for m in avchan.voice_members if not m.bot and m.id != after.id]},
                    name=int(time.time()))
                self.update_data(entry)
                if after.id not in self.names["member"].apply(str).values:
                    self.update_names(pandas.Series({"member": after.id, "username": after.name}))

    @commands.command(pass_context=True)
    async def update_namemap(self, ctx):
        server = ctx.message.server
        for uid in set(self.data["member"].append(pandas.Series([str(st) for row in self.data["present"] for st in row]))):
            uid = str(uid)
            if uid not in self.names["member"].apply(str).values:
                user = server.get_member(uid)
                self.update_names(pandas.Series({"member": uid, "username": user.name}))
        await self.bot.say("Namemap successfully updated!")

    @commands.command(pass_context=True)
    async def set_database_url(self, ctx, url):
        self.settings["database"] = url
        dataIO.save_json("data/member_logger/settings.json", self.settings)
        await self.bot.say("Database URL successfully changed.")


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

from discord.ext import commands
from random import choice
from .utils.dataIO import dataIO
from .utils import checks
from .utils.chat_formatting import box
from collections import Counter, defaultdict, namedtuple
import discord
import time
import os
import asyncio
import chardet
import requests
from lxml import html
from os.path import isfile, join
from os import listdir

DEFAULTS = {
    "MAX_SCORE": 10,
    "TIMEOUT": 120,
    "DELAY": 15,
    "BOT_PLAYS": False,
    "REVEAL_ANSWER": True
}

# this comment forces an update

class DamnDog:
    """General commands"""

    def __init__(self, bot):
        self.bot = bot
        self.damn_sessions = []
        self.file_path = "data/damn-dog/settings.json"
        settings = dataIO.load_json(self.file_path)
        self.settings = defaultdict(lambda: DEFAULTS.copy(), settings)

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def damnset(self, ctx):
        """Change DamnDog Settings"""
        server = ctx.message.server
        if ctx.invoked_subcommand is None:
            settings = self.settings[server.id]
            msg = box("Redbot gains points {BOT_PLAYS}\n"
                      "Seconds to answer: {DELAY}\n"
                      "Points to win: {MAX_SCORE}\n"
                      "Reveal answer on timeout: {REVEAL_ANSWER}\n"
                      "".format(**settings))
            msg += "\nSee {}help damnset to edit the settings".format(ctx.prefix)
            await self.bot.say(msg)

    @damnset.command(pass_context=True)
    async def maxscore(self, ctx, score: int):
        """Points required to win"""
        server = ctx.message.server
        if score > 0:
            self.settings[server.id]["MAX_SCORE"] = score
            self.save_settings()
            await self.bot.say("Points required to win set to {}".format(score))
        else:
            await self.bot.say("Score must be greater than 0.")

    @damnset.command(pass_context=True)
    async def timelimit(self, ctx, seconds: int):
        """Maximum seconds to answer"""
        server = ctx.message.server
        if seconds > 4:
            self.settings[server.id]["DELAY"] = seconds
            self.save_settings()
            await self.bot.say("Maximum seconds to answer set to {}".format(seconds))
        else:
            await self.bot.say("Seconds must be at least 5.")

    @damnset.command(pass_context=True)
    async def botplays(self, ctx):
        """Red gains points"""
        server = ctx.message.server
        if self.settings[server.id]["BOT_PLAYS"]:
            self.settings[server.id]["BOT_PLAYS"] = False
            await self.bot.say("Alright, I won't embarrass you at Damn.Dog anymore.")
        else:
            self.settings[server.id]["BOT_PLAYS"] = True
            await self.bot.say("I'll gain a point every time you don't answer in time.")
        self.save_settings()

    @damnset.command(pass_context=True)
    async def revealanswer(self, ctx):
        """Reveals answer to the question on timeout"""
        server = ctx.message.server
        if self.settings[server.id]["REVEAL_ANSWER"]:
            self.settings[server.id]["REVEAL_ANSWER"] = False
            await self.bot.say("I won't reveal the answer to the questions anymore.")
        else:
            self.settings[server.id]["REVEAL_ANSWER"] = True
            await self.bot.say("I'll reveal the answer if no one knows it.")
        self.save_settings()

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    async def damndog(self, ctx):
        """Start a damn.dog session"""
        message = ctx.message
        server = message.server
        session = self.get_damn_by_channel(message.channel)
        if not session:
            try:
                damn_questions = self.get_damn_data()
            except requests.RequestException:
                await self.bot.say("There was an error getting data from damn.dog")
            except Exception as e:
                print(e)
                await self.bot.say("There was an unknown error getting damn.dog data: {}".format(e))
            else:
                settings = self.settings[server.id]
                d = DamnSession(self.bot, damn_questions, message, settings)
                self.damn_sessions.append(d)
                await d.new_question()
        else:
            await self.bot.say("A damn.dog session is already ongoing in this channel.")

    @damndog.group(name="stop", pass_context=True, no_pm=True)
    async def damn_stop(self, ctx):
        """Stops an ongoing damndog session"""
        author = ctx.message.author
        server = author.server
        admin_role = self.bot.settings.get_server_admin(server)
        mod_role = self.bot.settings.get_server_mod(server)
        is_admin = discord.utils.get(author.roles, name=admin_role)
        is_mod = discord.utils.get(author.roles, name=mod_role)
        is_owner = author.id == self.bot.settings.owner
        is_server_owner = author == server.owner
        is_authorized = is_admin or is_mod or is_owner or is_server_owner

        session = self.get_damn_by_channel(ctx.message.channel)
        if session:
            if author == session.starter or is_authorized:
                await session.end_game()
                await self.bot.say("DamnDog stopped.")
            else:
                await self.bot.say("You are not allowed to do that.")
        else:
            await self.bot.say("There's no damndog session ongoing in this channel.")

    def get_damn_data(self):
        path = "data/damn-dog/img"
        onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
        img_dict = dict()
        for idx, fn in enumerate(onlyfiles):
            onlyfiles[idx] = fn.replace('-', ' ')[:-4]
            img_dict[onlyfiles[idx]] = fn
        return img_dict

    def get_damn_by_channel(self, channel):
        for d in self.damn_sessions:
            if d.channel == channel:
                return d
        return None

    async def on_message(self, message):
        if message.author != self.bot.user:
            session = self.get_damn_by_channel(message.channel)
            if session:
                await session.check_answer(message)

    async def on_damn_end(self, instance):
        if instance in self.damn_sessions:
            self.damn_sessions.remove(instance)

    def save_settings(self):
        dataIO.save_json(self.file_path, self.settings)


class DamnSession:
    def __init__(self, bot, damn_data, message, settings):
        self.bot = bot
        self.reveal_message = "The answer is {}."
        self.fail_message = "On to the next one..."
        self.correct_answer = None
        self.answer_set = set()
        self.answer_dict = dict()
        self.damn_data = damn_data
        self.channel = message.channel
        self.starter = message.author
        self.scores = Counter()
        self.status = "new question"
        self.timer = None
        self.timeout = time.perf_counter()
        self.count = 0
        self.settings = settings
        self.path = "data/damn-dog/img"

    async def stop_damn(self):
        self.status = "stop"
        self.bot.dispatch("damn_end", self)

    async def end_game(self):
        self.status = "stop"
        if self.scores:
            await self.send_table()
        self.bot.dispatch("damn_end", self)

    async def new_question(self):
        for score in self.scores.values():
            if score == self.settings["MAX_SCORE"]:
                await self.end_game()
                return True
        if self.damn_data == {}:
            await self.end_game()
            return True
        self.correct_answer = choice(list(self.damn_data.keys()))
        img = self.path + "/{}".format(self.damn_data[self.correct_answer])
        self.answer_set.add(self.correct_answer)
        del self.damn_data[self.correct_answer]
        for _ in range(4):
            self.answer_set.add(choice(list(self.damn_data.keys())))
        self.status = "waiting for answer"
        self.count += 1
        self.timer = int(time.perf_counter())
        await self.bot.send_file(destination=self.channel, fp=img)
        for idx, ans in enumerate(self.answer_set):
            idx = str(idx)
            self.answer_dict[ans] = idx
            await self.bot.say("{}. {}".format(idx, ans))

        while self.status != "correct answer" and (abs(self.timer - int(time.perf_counter()))) <= self.settings[
            "DELAY"]:
            if abs(self.timeout - int(time.perf_counter())) >= self.settings["TIMEOUT"]:
                await self.bot.say("I guess I'll stop then...")
                await self.stop_damn()
                return True
            await asyncio.sleep(1)  # Waiting for an answer or for the time limit
        if self.status == "correct answer":
            self.status = "new question"
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.new_question()
        elif self.status == "stop":
            return True
        else:
            if self.settings["REVEAL_ANSWER"]:
                msg = self.reveal_message.format(self.correct_answer)
            else:
                msg = self.fail_message
            if self.settings["BOT_PLAYS"]:
                msg += " **+1** for me!"
                self.scores[self.bot.user] += 1
            self.correct_answer = None
            await self.bot.say(msg)
            await self.bot.type()
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.new_question()

    async def send_table(self):
        t = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            t += "+ {}\t{}\n".format(user, score)
        await self.bot.say(box(t, lang="diff"))

    async def check_answer(self, message):
        if message.author == self.bot.user:
            return
        elif self.correct_answer is None:
            return

        self.timeout = time.perf_counter()
        has_guessed = False

        answer = self.correct_answer.lower()
        guess = message.content.lower()
        if guess == self.answer_dict[answer]:
            has_guessed = True

        if has_guessed:
            self.correct_answer = None
            self.status = "correct answer"
            self.scores[message.author] += 1
            msg = "You got it {}! **+1** to you!".format(message.author.name)
            await self.bot.send_message(message.channel, msg)


def check_folders():
    folders = ("data", "data/img/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    if not os.path.isfile("data/damn-dog/settings.json"):
        print("Creating empty settings.json")
        dataIO.save_json("data/damn-dog/settings.json", {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(DamnDog(bot))

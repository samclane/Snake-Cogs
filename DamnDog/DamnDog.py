import asyncio
import logging
import time
from collections import Counter
from os import listdir
from os.path import isfile, join
from random import choice

import discord
from redbot.core import Config, data_manager, checks, commands
from redbot.core.bot import Red
from redbot.core.utils import box


LOG = logging.getLogger("red.DamnDog")


class DamnDog(commands.Cog):
    """General commands"""

    def __init__(self, bot):
        super().__init__()
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=int(hash("DamnDog")))
        default_global = {
            "max_score": 10,
            "timeout": 120,
            "delay": 15,
            "bot_plays": False,
            "reveal_answer": True
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_global)
        self.img_path = str(data_manager.bundled_data_path(self)) + "\\img\\"

        self.damn_sessions = []

    @commands.group(no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def damnset(self, ctx):
        """Change DamnDog Settings"""
        if ctx.invoked_subcommand is None:
            msg = box("Redbot gains points: {}\n"
                      "Seconds to answer: {}\n"
                      "Points to win: {}\n"
                      "Seconds to timeout: {}\n"
                      "Reveal answer on timeout: {}\n"
                      "".format(await self.config.bot_plays(),
                                await self.config.delay(),
                                await self.config.max_score(),
                                await self.config.timeout(),
                                await self.config.reveal_answer()))
            msg += "\nSee {}help damnset to edit the settings".format(ctx.prefix)
            await ctx.send(msg)

    @damnset.command()
    async def maxscore(self, ctx, score: int):
        """Points required to win"""
        if score > 0:
            await self.config.max_score.set(score)
            await ctx.send("Points required to win set to {}".format(score))
        else:
            await ctx.send("Score must be greater than 0.")

    @damnset.command()
    async def timelimit(self, ctx, seconds: int):
        """Maximum seconds to answer"""
        if seconds > 4:
            await self.config.delay.set(seconds)
            await ctx.send("Maximum seconds to answer set to {}".format(seconds))
        else:
            await ctx.send("Seconds must be at least 5.")

    @damnset.command()
    async def botplays(self, ctx):
        """Red gains points"""
        if await self.config.bot_plays():
            await self.config.bot_plays.set(False)
            await ctx.send("Alright, I won't embarrass you at Damn.Dog anymore.")
        else:
            await self.config.bot_plays.set(True)
            await ctx.send("I'll gain a point every time you don't answer in time.")

    @damnset.command()
    async def revealanswer(self, ctx):
        """Reveals answer to the question on timeout"""
        if await self.config.reveal_answer():
            await self.config.reveal_answer.set(False)
            await ctx.send("I won't reveal the answer to the questions anymore.")
        else:
            await self.config.reveal_answer.set(True)
            await ctx.send("I'll reveal the answer if no one knows it.")

    @commands.group(invoke_without_command=True, no_pm=True)
    async def damndog(self, ctx):
        """Start a damn.dog session"""
        message = ctx.message
        session = self.get_damn_by_channel(message.channel)
        if not session:
            try:
                damn_questions = self.get_damn_data()
            except Exception as e:
                LOG.exception("Error getting damn.dog data...")
                await ctx.send("There was an unknown error getting damn.dog data: {}".format(e))
            else:
                config = self.config
                d = DamnSession(self, self.bot, damn_questions, ctx, config)
                self.damn_sessions.append(d)
                await d.new_question()
        else:
            await ctx.send("A damn.dog session is already ongoing in this channel.")

    @damndog.command(no_pm=True)
    async def stop(self, ctx):
        """Stops an ongoing damndog session"""
        author = ctx.message.author
        guild = author.guild
        is_server_owner = author == guild.owner
        is_admin = await self.bot.is_admin(author)
        is_mod = await self.bot.is_mod(author)
        is_owner = await self.bot.is_owner(author)
        is_authorized = is_admin or is_mod or is_owner or is_server_owner

        session = self.get_damn_by_channel(ctx.message.channel)
        if session:
            if author == session.starter or is_authorized:
                await session.end_game()
                await ctx.send("DamnDog stopped.")
            else:
                await ctx.send("You are not allowed to do that.")
        else:
            await ctx.send("There's no damndog session ongoing in this channel.")

    def get_damn_data(self):
        onlyfiles = [f for f in listdir(self.img_path) if isfile(join(self.img_path, f))]
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
        if not message.author.bot:
            session = self.get_damn_by_channel(message.channel)
            if session:
                await session.check_answer(message)

    async def on_damn_end(self, instance):
        if instance in self.damn_sessions:
            self.damn_sessions.remove(instance)


class DamnSession:
    def __init__(self, cog, bot, damn_data, context, config):
        self.cog = cog
        self.bot = bot
        self.reveal_message = "The answer is {}."
        self.fail_message = "On to the next one..."
        self.correct_answer = None
        self.answer_set = set()
        self.answer_dict = dict()
        self.has_answered = set()
        self.damn_data = damn_data
        self.context = context
        self.channel = context.message.channel
        self.starter = context.message.author
        self.scores = Counter()
        self.status = "new question"
        self.timer = None
        self.timeout = time.perf_counter()
        self.count = 0
        self.config = config
        self.img_path = str(data_manager.bundled_data_path(self.cog)) + "\\img\\"

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
            if score == await self.config.max_score():
                await self.end_game()
                return True
        if self.damn_data == {}:
            await self.end_game()
            return True
        self.correct_answer = choice(list(self.damn_data.keys()))
        img = self.img_path + "/{}".format(self.damn_data[self.correct_answer])
        self.answer_set.add(self.correct_answer)
        del self.damn_data[self.correct_answer]
        for _ in range(3):
            self.answer_set.add(choice(list(self.damn_data.keys())))
        self.status = "waiting for answer"
        self.count += 1
        self.timer = int(time.perf_counter())
        await self.context.send(file=discord.File(fp=img, filename="damn-image.jpg"))
        msg = "Choices:\n"
        for idx, ans in enumerate(self.answer_set, 1):
            idx = str(idx)
            self.answer_dict[ans] = idx
            msg += "**{}.** {}\n".format(idx, ans)
        await self.context.send(msg)

        while self.status != "correct answer" and (
        abs(self.timer - int(time.perf_counter()))) <= await self.config.delay():
            if abs(self.timeout - int(time.perf_counter())) >= await self.config.timeout():
                await self.context.send("I guess I'll stop then...")
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
            if await self.config.reveal_answer():
                msg = self.reveal_message.format(self.correct_answer)
            else:
                msg = self.fail_message
            if await self.config.bot_plays():
                msg += " **+1** for me!"
                self.scores[self.bot.user] += 1
            self.reset_round()
            await self.context.send(msg)
            self.context.typing()
            await asyncio.sleep(3)
            if not self.status == "stop":
                await self.new_question()

    async def send_table(self):
        t = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            t += "+ {}\t{}\n".format(user, score)
        await self.context.send(box(t, lang="diff"))

    async def check_answer(self, message):
        if self.correct_answer is None:
            return
        elif message.author in self.has_answered:
            return

        self.timeout = time.perf_counter()
        has_guessed = False

        answer = self.correct_answer.lower()
        guess = message.content.lower()
        if guess == self.answer_dict[answer]:
            has_guessed = True

        if has_guessed:
            self.status = "correct answer"
            self.scores[message.author] += 1
            msg = "The correct answer was \"{}\"\n".format(self.correct_answer)
            msg += "You got it {}! **+1** to you!".format(message.author.name)
            await self.context.send(msg)
            self.reset_round()
        else:
            self.has_answered.add(message.author)

    def reset_round(self):
        self.correct_answer = None
        self.answer_dict = dict()
        self.answer_set = set()
        self.has_answered = set()

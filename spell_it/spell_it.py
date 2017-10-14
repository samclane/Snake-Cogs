import re


class SpellIt:
    def __init__(self, bot):
        self.bot = bot

    async def message_recv(self, message):
        content = message.content
        if message.author.bot:
            return
        user = message.author

        regex = r"^.* ?[i|I]'?[m|M] (.+)$"
        matches = re.finditer(regex, content)
        for matchNum, match in enumerate(matches):
            await self.bot.send_message(message.channel, "Hi{}, I'm dad!".format(match.group(1)))

        if 'bb' in content or 'BB' in content or 'bB' in content or 'Bb' in content:
            meme_ref = 'bb'
        elif 'pp' in content or 'PP' in content or 'pP' in content or 'Pp' in content:
            meme_ref = 'pp'
        else:
            return
        await self.bot.send_message(message.channel, "{} you said {}".format(user.mention, meme_ref))


def setup(bot):
    n = SpellIt(bot)
    bot.add_listener(n.message_recv, "on_message")
    bot.add_cog(n)

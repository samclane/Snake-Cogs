import asyncio
import random
import re
from subprocess import call

import discord
from gtts import gTTS
from redbot.core import Config, data_manager, checks, commands


class ProfanitiesFilter(object):
    def __init__(self, filterlist, ignore_case=True, replacements="$@%-?!",
                 complete=True, inside_words=False):
        """
        Inits the profanity filter.

        filterlist -- a list of regular expressions that
        matches words that are forbidden
        ignore_case -- ignore capitalization
        replacements -- string with characters to replace the forbidden word
        complete -- completely remove the word or keep the first and last char?
        inside_words -- search inside other words?

        """

        self.badwords = filterlist
        self.ignore_case = ignore_case
        self.replacements = replacements
        self.complete = complete
        self.inside_words = inside_words

    def _make_clean_word(self, length):
        """
        Generates a random replacement string of a given length
        using the chars in self.replacements.

        """
        return ''.join([random.choice(self.replacements) for i in
                        range(length)])

    def __replacer(self, match):
        value = match.group()
        if self.complete:
            return self._make_clean_word(len(value))
        else:
            return value[0] + self._make_clean_word(len(value) - 2) + value[-1]

    def clean(self, text):
        """Cleans a string from profanity."""

        regexp_insidewords = {
            True: r'(%s)',
            False: r'\b(%s)\b',
        }

        regexp = (regexp_insidewords[self.inside_words] %
                  '|'.join(self.badwords))

        r = re.compile(regexp, re.IGNORECASE if self.ignore_case else 0)

        return r.sub(self.__replacer, text)


emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)

locales = {
    'af': 'Afrikaans',
    'sq': 'Albanian',
    'ar': 'Arabic',
    'hy': 'Armenian',
    'bn': 'Bengali',
    'ca': 'Catalan',
    'zh': 'Chinese',
    'zh-cn': 'Chinese (Mandarin/China)',
    'zh-tw': 'Chinese (Mandarin/Taiwan)',
    'zh-yue': 'Chinese (Cantonese)',
    'hr': 'Croatian',
    'cs': 'Czech',
    'da': 'Danish',
    'nl': 'Dutch',
    'en': 'English',
    'en-au': 'English (Australia)',
    'en-uk': 'English (United Kingdom)',
    'en-us': 'English (United States)',
    'eo': 'Esperanto',
    'fi': 'Finnish',
    'fr': 'French',
    'de': 'German',
    'el': 'Greek',
    'hi': 'Hindi',
    'hu': 'Hungarian',
    'is': 'Icelandic',
    'id': 'Indonesian',
    'it': 'Italian',
    'ja': 'Japanese',
    'km': 'Khmer (Cambodian)',
    'ko': 'Korean',
    'la': 'Latin',
    'lv': 'Latvian',
    'mk': 'Macedonian',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'ru': 'Russian',
    'sr': 'Serbian',
    'si': 'Sinhala',
    'sk': 'Slovak',
    'es': 'Spanish',
    'es-es': 'Spanish (Spain)',
    'es-us': 'Spanish (United States)',
    'sw': 'Swahili',
    'sv': 'Swedish',
    'ta': 'Tamil',
    'th': 'Thai',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'vi': 'Vietnamese',
    'cy': 'Welsh'
}

voices = [
    'm1',
    'm2',
    'm3',
    'm4',
    'm5',
    'm6',
    'm7',
    'f1',
    'f2',
    'f3',
    'f4',
    'croak',
    'whisper'
]


class OnJoin(commands.Cog):
    """Uses TTS to announce when a user joins the channel, like Teamspeak or Ventrillo"""

    def __init__(self, bot):
        self.bot = bot
        self.audio_players = {}
        self.config = Config.get_conf(self, identifier=int(hash("on_join")))
        default_global = {
            "locale": "en-us",
            "voice": "ml",
            "speed": 175,
            "allow_emoji": "on",
            "profanity_filter": "off",
            "profanity_list": [],
            "use_espeak": "off"
        }
        self.config.register_global(**default_global)
        self.config.register_guild(**default_global)
        self.save_path = data_manager.cog_data_path(self)

    async def string_to_speech(self, text):
        """ Create TTS mp3 file `temp_message.mp3` """
        use_espeak = await self.config.use_espeak()
        text = text.lower()
        if use_espeak == "off":
            try:
                tts = gTTS(text=text, lang=await self.config.locale())
                tts.save(str(self.save_path) + "/temp_message.mp3")
            except AttributeError:  # If there's a problem with gTTS, use espeak instead
                use_espeak = "on"
        if use_espeak == "on":
            call(['espeak -v{}+{} -s{} "{}" --stdout > {}'.format(await self.config.locale(), await self.config.voice(),
                                                                  await self.config.speed(), text,
                                                                  str(self.save_path) + "temp_message.mp3")],
                 shell=True)

    def voice_channel_full(self, voice_channel: discord.VoiceChannel) -> bool:
        return (voice_channel.user_limit != 0 and
                len(voice_channel.members) >= voice_channel.user_limit)

    def voice_connected(self, server: discord.Guild) -> bool:
        if server.voice_client is None:
            return False
        return server.voice_client.is_connected()

    def voice_client(self, server: discord.Guild) -> discord.VoiceClient:
        return server.voice_client

    async def _leave_voice_channel(self, server: discord.Guild):
        if not self.voice_connected(server):
            return
        voice_client = self.voice_client(server)

        if server.id in self.audio_players:
            self.audio_players[server.id].stop()
        await voice_client.disconnect()

    async def wait_for_disconnect(self, server: discord.Guild):
        while self.audio_players[server.id].is_playing():
            await asyncio.sleep(0.1)
        await self._leave_voice_channel(server)

    async def sound_init(self, server: discord.Guild, path: str):
        options = "-filter \"volume=volume=1.00\""
        voice_client = self.voice_client(server)
        voice_client.play(discord.FFmpegPCMAudio(path, options=options))
        self.audio_players[server.id] = voice_client

    async def sound_play(self, server: discord.Guild,
                         channel: discord.VoiceChannel, p: str):
        if self.voice_channel_full(channel):
            return

        if isinstance(channel, discord.VoiceChannel):
            if self.voice_connected(server):
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
            else:
                await channel.connect()
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)

            await asyncio.sleep(5)
            await self.wait_for_disconnect(server)

    async def voice_state_update(self, member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        if before.channel != after.channel:

            name = member.display_name
            if await self.config.allow_emoji() == 'off':
                name = emoji_pattern.sub(r'', name)
            if await self.config.profanity_filter() == 'on':
                f = ProfanitiesFilter(await self.config.profanity_filter(), replacements=" ")
                f.inside_words = True
                name = f.clean(name)

            if after.channel:
                text = "{} has joined the channel".format(name)
                channel = after.channel

                await self.string_to_speech(text)
                await self.sound_play(channel.guild, channel, str(self.save_path) + "/temp_message.mp3")

            if before.channel:
                text = "{} has left the channel".format(name)
                channel = before.channel

                await self.string_to_speech(text)
                await self.sound_play(channel.guild, channel, str(self.save_path) + "/temp_message.mp3")

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(pass_context=True, name='say')
    async def say(self, ctx: commands.Context, *, message):
        """Have the bot use TTS say a string in the current voice channel."""
        server = ctx.message.author.Guild
        channel = ctx.message.author.voice_channel
        await self.string_to_speech(message)
        await self.sound_play(server, channel, str(self.save_path) + "/temp_message.mp3")

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(pass_context=False, name='set_locale')
    async def set_locale(self, ctx, locale):
        """Change the TTS speech locale region."""
        if locale not in locales.keys():
            await ctx(
                "{} was not found in the list of locales. Look at https://pypi.python.org/pypi/gTTS"
                " for a list of valid codes.".format(
                    locale))
            return
        else:
            await self.config.locale.set(locale)
            await ctx("Locale was successfully changed to {}.".format(locales[locale]))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(pass_context=False, name='set_voice')
    async def set_voice(self, ctx, voice):
        """ Change the voice style of the espeak narrator. Valid selections are m(1-7), f(1-4), croak, and whisper."""
        if voice not in voices:
            await ctx("{} is not a valid voice code."
                      "Please choose one of the following:\n {}".format(voice, '\n'.join(voices)))
            return
        else:
            await self.config.voice.set(voice)
            await ctx("Voice was successfully changed to {}.".format(voice))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name='set_speed')
    async def set_speed(self, ctx, speed):
        """ Set the WPM speed of the espeak narrator. Range is 80-500. """
        speed = int(speed)
        if not (80 < speed < 500):
            await ctx("{} is not between 80 and 500 WPM.".format(speed))
            return
        else:
            await self.config.speed.set(speed)
            await ctx("Speed was successfully changed to {}.".format(speed))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(pname='allow_emoji')
    async def allow_emoji(self, ctx, setting):
        """Change if emojis will be pronounced in names (IN PROGRESS)."""
        setting = setting.lower()
        if setting not in ["on", "off"]:
            await ctx("Please specify if you want emojis 'on' or 'off'")
            return
        else:
            if setting == "on":
                await self.config.allow_emoji.set('on')
            elif setting == "off":
                await self.config.allow_emoji.set('off')
            await ctx("Emoji speech is now {}.".format(setting))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name='set_filter')
    async def set_filter(self, ctx, setting):
        """Change slurs will be pronounced in names (IN PROGRESS)."""
        setting = setting.lower()
        if setting not in ["on", "off"]:
            await ctx.send("Please specify if you want the profanity filter 'on' or 'off'")
            return
        else:
            if setting == "on":
                await self.config.profanity_filter.set('on')
            elif setting == "off":
                await self.config.profanity_filter.set('off')
            await ctx.send("Profanity filter is now {}.".format(setting))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name='add_filter')
    async def add_filter(self, ctx, word):
        """ Add a word to the censor filter. """
        word = word.lower()
        if word not in await self.config.profanity_list():
            async with await self.config.profanity_list() as p_list:
                p_list.append(word)
            await ctx.send("{} has been added to the profanity filter.".format(word.capitalize()))
        else:
            await ctx.send("{} is already in the profanity dictionary.".format(word.capitalize()))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="use_espeak")
    async def use_espeak(self, ctx, setting):
        """ Manually toggle espeak 'on' or 'off'. """
        setting = setting.lower()
        if setting not in ["on", "off"]:
            await ctx.send("Please specify if you want to use espeak (yes) or gTTS( no).")
            return
        else:
            if setting == "on":
                await self.config.use_espeak.set('on')
            elif setting == "off":
                await self.config.use_espeak.set('off')
        await ctx.send("Now using {} as the TTS engine".format("espeak" if setting == "on" else "gTTS"))

import asyncio
import os
import re

import discord
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from gtts import gTTS

from .utils import checks

emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"
                           u"\U0001F300-\U0001F5FF"
                           u"\U0001F680-\U0001F6FF"
                           u"\U0001F1E0-\U0001F1FF"
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


class OnJoin:
    """Uses gTTS to announce when a user joins the channel, like Teamspeak or Ventrillo"""

    def __init__(self, bot):
        self.bot = bot
        self.audio_players = {}
        self.settings = dataIO.load_json("data/on_join/settings.json")

        self.save_path = "data/on_join/"
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

        if "locale" not in self.settings.keys():
            self.settings["locale"] = "en-us"
        if "allow_emoji" not in self.settings.keys():
            self.settings["allow_emoji"] = True

    def voice_channel_full(self, voice_channel: discord.Channel) -> bool:
        return (voice_channel.user_limit != 0 and
                len(voice_channel.voice_members) >= voice_channel.user_limit)

    def voice_connected(self, server: discord.Server) -> bool:
        return self.bot.is_voice_connected(server)

    def voice_client(self, server: discord.Server) -> discord.VoiceClient:
        return self.bot.voice_client_in(server)

    async def _leave_voice_channel(self, server: discord.Server):
        if not self.voice_connected(server):
            return
        voice_client = self.voice_client(server)

        if server.id in self.audio_players:
            self.audio_players[server.id].stop()
        await voice_client.disconnect()

    async def wait_for_disconnect(self, server: discord.Server):
        while not self.audio_players[server.id].is_done():
            await asyncio.sleep(0.01)
        await self._leave_voice_channel(server)

    async def sound_init(self, server: discord.Server, path: str):
        options = "-filter \"volume=volume=1.00\""
        voice_client = self.voice_client(server)
        self.audio_players[server.id] = voice_client.create_ffmpeg_player(
            path, options=options, use_avconv=True)

    async def sound_play(self, server: discord.Server,
                         channel: discord.Channel, p: str):
        if self.voice_channel_full(channel):
            return

        if not channel.is_private:
            if self.voice_connected(server):
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    # await self.wait_for_disconnect(server)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    # await self.wait_for_disconnect(server)
            else:
                await self.bot.join_voice_channel(channel)
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    # await self.wait_for_disconnect(server)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    # await self.wait_for_disconnect(server)

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
            if not self.settings["allow_emoji"]:
                text = emoji_pattern.sub(r'', text)
            tts = gTTS(text=text, lang=self.settings["locale"])
            tts.save(self.save_path + "/temp_message.mp3")
            await self.sound_play(server, channel, self.save_path + "/temp_message.mp3")

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=True, no_pm=True, name='seals')
    async def seals(self, ctx: commands.Context):
        """For when it's time to put someone in their place."""
        server = ctx.message.author.server
        channel = ctx.message.author.voice_channel
        await self.sound_play(server, channel,
                              self.save_path + "/seals.mp3")

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=True, no_pm=True, name='say')
    async def say(self, ctx: commands.Context, *, message):
        """Have the bot use TTS say a string in the current voice channel."""
        server = ctx.message.author.server
        channel = ctx.message.author.voice_channel
        tts = gTTS(text=message, lang=self.settings["locale"])
        tts.save(self.save_path + "/temp_message.mp3")
        await self.sound_play(server, channel, self.save_path + "/temp_message.mp3")

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=False, no_pm=True, name='set_locale')
    async def set_locale(self, locale):
        """Change the TTS speech locale region."""
        if locale not in locales.keys():
            await self.bot.say(
                "{} was not found in the list of locales. Look at https://pypi.python.org/pypi/gTTS"
                " for a list of valid codes.".format(
                    locale))
            return
        else:
            self.settings["locale"] = locale
            dataIO.save_json("data/on_join/settings.json", self.settings)
            await self.bot.say("Locale was successfully changed to {}.".format(locales[locale]))

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=False, no_pm=True, name='allow_emoji')
    async def allow_emoji(self, setting):
        """Change if emojis will be pronounced in names (IN PROGRESS)."""
        setting = setting.lower()
        if setting not in ["on", "off"]:
            await self.bot.say("Please specify if you want emojis 'on' or 'off'")
            return
        else:
            if setting is "on":
                self.settings["allow_emoji"] = True
            elif setting is "off":
                self.settings["allow_emoji"] = False
            dataIO.save_json("data/on_join.settings.json", self.settings)
            await self.bot.say("Emoji speech is now {}.".format(setting))


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

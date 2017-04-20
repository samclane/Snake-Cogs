import discord
from discord.ext import commands
from gtts import gTTS
import os
import asyncio
import speech_recognition as sr
from .utils import checks


class SoundPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.audio_players = {}

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
            path, options=options)

    async def sound_play(self, server: discord.Server,
                          channel: discord.Channel, p: str):
        if self.voice_channel_full(channel):
            return

        if not channel.is_private:
            if self.voice_connected(server):
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
            else:
                await self.bot.join_voice_channel(channel)
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()


class TalkBack:
    def __init__(self, bot):
        self.bot = bot
        self.recognizer = sr.Recognizer()

    def speak(self, audio_string, ctx):
        sp = SoundPlayer(self.bot)
        tts = gTTS(text=audio_string, lang='en')
        tts.save("audio.mp3")
        sp.sound_play(ctx.message.server, ctx.message.author.voice_channel, "audio.mp3")

    def record_audio(self):
        with sr.Microphone as source:
            print("Say something!")
        audio = self.recognizer.listen(source)

        data = ""
        try:
            data = self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            print("Google speech recognition could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))

        return data

    def audio_commands(self, data, ctx):
        if "Hello Red" in data:
            print("Hello world!")
            self.speak("Hello world!", ctx)

    @commands.command(pass_context=True, no_pm=True, name='get_in_here')
    async def get_in_here(self, ctx: commands.Context):
        author = ctx.message.author
        server = ctx.message.server
        voice_channel = author.voice_channel
        if self.bot.get_channel(server.id) is None or self.bot.get_channel(server.id) is not voice_channel:
            try:
                await asyncio.wait_for(self.bot.join_voice_channel(voice_channel), timeout=5, loop=self.bot.loop)
            except asyncio.futures.TimeoutError as e:
                raise ConnectionError("Error connecting to voice channel; " + e)
        data = self.record_audio()
        self.audio_commands(data, ctx)

def setup(bot):
    n = TalkBack(bot)
    bot.add_cog(n)

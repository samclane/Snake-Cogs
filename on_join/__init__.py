from .on_join import OnJoin


def setup(bot):
    n = OnJoin(bot)
    bot.add_listener(n.voice_state_update, "on_voice_state_update")
    bot.add_cog(n)
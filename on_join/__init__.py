from redbot.core.bot import Red

from .on_join import OnJoin


async def setup(bot: Red):
    if bot.get_cog("on_join"):
        print("on_join already loaded, attempting to unload first...")
        bot.remove_cog("on_join")
        await bot.remove_loaded_package("on_join")
        bot.unload_extension("on_join")

    n = OnJoin(bot)
    bot.add_listener(n.voice_state_update, "on_voice_state_update")
    bot.add_cog(n)

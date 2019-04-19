from redbot.core.bot import Red

from .OnJoin import OnJoin


async def setup(bot: Red):
    if bot.get_cog("OnJoin"):
        print("OnJoin already loaded, attempting to unload first...")
        bot.remove_cog("OnJoin")
        await bot.remove_loaded_package("OnJoin")
        bot.unload_extension("OnJoin")

    n = OnJoin(bot)
    bot.add_listener(n.voice_state_update, "on_voice_state_update")
    bot.add_cog(n)

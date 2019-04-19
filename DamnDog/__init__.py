from redbot.core.bot import Red

from .DamnDog import DamnDog


async def setup(bot: Red):
    if bot.get_cog("DamnDog"):
        print("DamnDog already loaded, attempting to unload first...")
        bot.remove_cog("DamnDog")
        await bot.remove_loaded_package("DamnDog")
        bot.unload_extension("DamnDog")

    n = DamnDog(bot)
    bot.add_cog(n)

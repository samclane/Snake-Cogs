from redbot.core.bot import Red

from .damn_dog import DamnDog


async def setup(bot: Red):
    if bot.get_cog("damn_dog"):
        print("damn_dog already loaded, attempting to unload first...")
        bot.remove_cog("damn_dog")
        await bot.remove_loaded_package("damn_dog")
        bot.unload_extension("damn_dog")

    n = DamnDog(bot)
    bot.add_cog(n)

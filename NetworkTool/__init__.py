import asyncio

import websockets

from .NetworkTool import NetworkTool


def setup(bot):
    n = NetworkTool(bot)

    try:
        asyncio.get_event_loop().run_until_complete(websockets.serve(n.hello, 'localhost', 8785))
    except RuntimeError:
        pass

    bot.add_cog(n)

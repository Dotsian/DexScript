from typing import TYPE_CHECKING

from .cog import DexScript

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

__version__ = "1.0.0"


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(DexScript(bot, __version__))

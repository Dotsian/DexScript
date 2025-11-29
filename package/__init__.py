from typing import TYPE_CHECKING

from .cog import DexScript

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(DexScript(bot))

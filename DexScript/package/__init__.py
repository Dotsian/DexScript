from .cog import DexScript


async def setup(bot):
    await bot.add_cog(DexScript(bot))

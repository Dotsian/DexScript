from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

ASSET_PATH = "https://raw.githubusercontent.com/Dotsian/DexScript/refs/heads/main/assets"


class DexScript(commands.Cog):
    """
    DexScript commands.
    """

    def __init__(self, bot: "BallsDexBot", version: str):
        self.bot = bot
        self.version = version

    @commands.command()
    @commands.is_owner()
    async def run(self, ctx: commands.Context["BallsDexBot"], code: str):
        """
        Executes DexScript code.

        Parameters
        ----------
        code: str
            The code you want to execute.
        """
        pass

    @commands.command()
    async def dexscript(self, ctx: commands.Context["BallsDexBot"]):
        """
        Displays information about DexScript.
        """
        guide_link = "https://github.com/Dotsian/DexScript/wiki/Commands"
        discord_link = "https://discord.gg/EhCxuNQfzt"

        description = (
            "DexScript is a set of commands for Ballsdex created by DotZZ "
            "that expands on the standalone admin commands and substitutes for the admin panel "
            "in terms of modifying data. It simplifies editing, adding, deleting, and displaying "
            "data for models such as balls, regimes, specials, etc.\n\n"
            f"Refer to the official [DexScript guide](<{guide_link}>) for information "
            f"about DexScript's functionality\n\n"
            "If you want to follow DexScript, join the official "
            f"[DexScript Discord server](<{discord_link}>)."
        )

        embed = discord.Embed(
            title="DexScript", description=description, color=discord.Color.from_str("#03BAFC")
        )

        embed.set_thumbnail(url=f"{ASSET_PATH}/DexScriptLogo.png")
        embed.set_footer(text=f"DexScript {self.version}")

        await ctx.send(embed=embed)

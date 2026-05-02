import base64
import re
import traceback

import discord
import requests
from discord.ext import commands

from settings.models import settings

from .parser import DexScriptParser
from .utils import Utils, config

__version__ = "0.5.1"

GITHUB = "Caylies/DexScript"


class DexScript(commands.Cog):
    """
    DexScript commands
    """

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def check_version():
        if not config.versioncheck:
            return None

        request = requests.get(
            f"https://api.github.com/repos/{GITHUB}/contents/pyproject.toml", {"ref": config.reference}
        )

        if request.status_code != requests.codes.ok:
            return

        toml_content = base64.b64decode(request.json()["content"]).decode()
        new_version = re.search(r'version\s*=\s*"(.*?)"', toml_content).group(1)

        if new_version != __version__:
            return f"Your DexScript version ({__version__}) is outdated. Please update to version ({new_version})"

        return None

    @commands.command()
    @commands.is_owner()
    async def run(self, ctx: commands.Context, *, code: str):
        """
        Executes DexScript code.

        Parameters
        ----------
        code: str
          The code you want to execute.
        """
        body = Utils.remove_code_markdown(code)

        version_check = self.check_version()

        if version_check:
            await ctx.send(f"-# {version_check}")

        dexscript_instance = DexScriptParser(ctx, self.bot)

        try:
            result = await dexscript_instance.execute(body)
        except Exception as error:
            full_error = traceback.format_exc() if config.debug else error

            await ctx.send(f"```ERROR: {full_error}```")
            return
        else:
            if result is not None:
                await ctx.send(f"```ERROR: {result}```")
                return

            await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def about(self, ctx: commands.Context):
        """
        Displays information about DexScript.
        """
        guide_link = f"https://github.com/{GITHUB}/wiki/Commands"
        discord_link = "https://discord.gg/EhCxuNQfzt"

        description = (
            "DexScript is a DSL package for Ballsdex created by Cayla that allows you to easily perform operations "
            "on balls, regimes, specials, etc.\n\n"
            f"Refer to the official [DexScript guide](<{guide_link}>) for information "
            f"about DexScript's functionality\n"
            "If you want to follow DexScript or require assistance, join the official "
            f"[DexScript Discord server](<{discord_link}>)."
        )

        embed = discord.Embed(
            title="DexScript - BETA", description=description, color=discord.Color.from_str("#03BAFC")
        )

        version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

        embed.set_thumbnail(
            url=f"https://raw.githubusercontent.com/{GITHUB}/refs/heads/{config.reference}/assets/DexScriptLogo.png"
        )

        embed.set_footer(text=f"DexScript {__version__} ({version_check}) • Ballsdex 3.0")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def setting(self, ctx: commands.Context, setting: str, value: str | None = None):
        """
        Changes a setting based on the value provided.

        Parameters
        ----------
        setting: str
          The setting you want to toggle.
        value: str | None
          The value you want to set the setting to.
        """
        setting = setting.lower()

        if setting not in vars(config):
            await ctx.send(f"`{setting}` is not a valid setting.")
            return

        setting_value = vars(config)[setting]
        new_value = value

        if isinstance(setting_value, bool):
            new_value = bool(value) if value else not setting_value

        setattr(config, setting, new_value)

        await ctx.send(f"`{setting}` has been set to `{new_value}`")

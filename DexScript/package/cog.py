import base64
import re
import traceback

import discord
import requests
from discord.ext import commands

from .parser import DexScriptParser
from .utils import DIR, Utils, config

if DIR == "ballsdex":
    from ballsdex.settings import settings
else:
    from carfigures.settings import settings


__version__ = "0.5"


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

        r = requests.get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/pyproject.toml",
            {"ref": config.reference},
        )

        if r.status_code != requests.codes.ok:
            return

        toml_content = base64.b64decode(r.json()["content"]).decode("UTF-8")
        new_version = re.search(r'version\s*=\s*"(.*?)"', toml_content).group(1)

        if new_version != __version__:
            return (
                f"Your DexScript version ({__version__}) is outdated. "
                f"Please update to version ({new_version}) "
                f"by running `{settings.prefix}upgrade`"
            )

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
        guide_link = "https://github.com/Dotsian/DexScript/wiki/Commands"
        discord_link = "https://discord.gg/EhCxuNQfzt"

        description = (
            "DexScript is a set of commands for Ballsdex and CarFigures created by DotZZ "
            "that expands on the standalone admin commands and substitutes for the admin panel. "
            "It simplifies editing, adding, deleting, and displaying data for models such as "
            "balls, regimes, specials, etc.\n\n"
            f"Refer to the official [DexScript guide](<{guide_link}>) for information "
            f"about DexScript's functionality or use `{settings.prefix}run HELP` to display "
            "a list of all commands and what they do.\n"
            f"To update DexScript, run `{settings.prefix}upgrade`.\n\n"
            "If you want to follow DexScript or require assistance, join the official "
            f"[DexScript Discord server](<{discord_link}>)."
        )

        embed = discord.Embed(
            title="DexScript - BETA",
            description=description,
            color=discord.Color.from_str("#03BAFC"),
        )

        version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

        embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
        embed.set_footer(text=f"DexScript {__version__} ({version_check})")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def upgrade(self, ctx: commands.Context):
        link = "https://api.github.com/repos/Dotsian/DexScript/contents/DexScript/github/installer.py"
        content = requests.get(link, {"ref": config.reference}).json()["content"]
        
        await ctx.invoke(self.bot.get_command("eval"), body=base64.b64decode(content).decode())

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

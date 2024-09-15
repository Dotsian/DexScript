import discord
import logging
import os
import re
import enum

from discord.ext import commands

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
    from ballsdex.core.models import Ball
else:
    from carfigures.core.models import Car as Ball

log = logging.getLogger(f"{dir_type}.core.dexscript")

__version__ = "0.1.2"


CORE_PATH = os.path.dirname(os.path.abspath(__file__))
START_CODE_BLOCK_RE = re.compile(r"^((```py(thon)?)(?=\s)|(```))")

METHODS = [
    "UPDATE",
    "REMOVE",
    "DISPLAY"
]


class TOKENS(enum.Enum):
    METHOD = "METHOD"
    NUMBER = "NUMBER"
    STRING = "STRING"


class DexScriptParser():
    """
    Class used for parsing DexScript contents into Python code.
    Ported over from DotZZ's DexScript Migrations JavaScript file.
    """

    def __init__(self, ctx: commands.Context, code: str):
        self.code = code
        self.fields = []
        self.ctx = ctx

    def format_class(self, field):
        """
        Returns a class's identifier. 
        If there is a token attached to the class, it will exclude the token.

        Parameters
        ----------
        field: str
            The class you want to use.
        """

        return (field[0] if isinstance(field, tuple) else field)

    def grab_token(self, line):
        """
        Grabs the token based on a string provided.

        Parameters
        ----------
        line: str
            The string you want to grab the token from.
        """

        token = TOKENS.STRING
        
        if self.format_class(line) in METHODS:
            token = TOKENS.METHOD
        elif isinstance(line, int) or isinstance(line, float):
            token = TOKENS.NUMBER

        return (line, token)
    
    def parse_code(self):
        """
        Parses a DexScript Migration file and converts it into a readable list.
        """

        tracked_field = None
        class_name = ""
        class_data = {}

        for index, field in enumerate(self.fields):
            previous_field = self.fields[index - 1]

            if previous_field is not None and previous_field[1] == TOKENS.METHOD:
                tracked_field = previous_field

            if tracked_field is None or tracked_field[1] != TOKENS.METHOD:
                continue

            formatted_class = self.format_class(tracked_field)

            if class_name == "":
                class_name = field[0]

                try:
                    class_data[formatted_class]
                except Exception:
                    class_data[formatted_class] = {}

                class_data[formatted_class][class_name] = []

            class_data[formatted_class][class_name].append(field[0])

        return class_data

    def parse(self, code: str):
        if not "\n" in code:
            code = "\n" + code

        for line1 in code.split("\n"): 
            if line1.startswith("//") or line1 == "" or line1 == "\n":
                continue

            for line2 in line1.split(" > "):
                self.fields.append(self.grab_token(line2.replace("    ", "")))

        return self.parse_code()
    
    async def execute(self, key, item):
        formatted_ball = item["BALL"]

        filters = {}

        if dir_type == "ballsdex":
            filters["country"] == formatted_ball[1]
        else:
            filters["full_name"] == formatted_ball[1]

        get_model = await Ball.get(**filters)

        match key:
            case "UPDATE":
                setattr(get_model, formatted_ball[2].lower(), formatted_ball[3])

                await get_model.save()

                await self.ctx.send(f"Updated `{formatted_ball[1]}'s` {formatted_ball[2]}")

            case "REMOVE":
                await get_model.delete()

                await self.ctx.send(f"Deleted `{formatted_ball[1]}`")

            case "DISPLAY":
                await self.ctx.send(f"```{getattr(get_model, formatted_ball[2].lower())}```")

    async def run(self):
        code_fields = self.parse(self.code)

        for key, field in code_fields.items():
           await self.execute(key, field)


class DexScript(commands.Cog):
    """
    DexScript support
    """

    def __init__(self, bot):
        self.bot = bot

    # TODO: Migrate this function over to the utilities path 
    # so there aren't any duplicates.
    @staticmethod
    def cleanup_code(content): 
        """
        Automatically removes code blocks from the code.
        """

        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        return content.strip("` \n")

    @commands.command()
    @commands.is_owner()
    async def run(self, ctx: commands.Context, *, code: str):
        """
        Executes DexScript code.
        """

        body = self.cleanup_code(code)

        try:
            dexscript_instance = DexScriptParser(ctx, body)
            await dexscript_instance.run()
        except Exception as e:
            await ctx.send(f"```\n{e}\n```")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def about(self, ctx: commands.Context):
        embed = discord.Embed(
            title="DexScript - ALPHA",
            description=(
                "DexScript is a set of commands created by DotZZ that allows you to easily "
                "modify, delete, and display data about balls.\n\n"
                "For a guide on how to use DexScript, refer to the guide on the [DexScript GitHub Page](<https://github.com/DotZZ-alt/DexScript>)"
            ),
            color = discord.Color.from_str("#03BAFC")
        )

        embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
        embed.set_footer(text=f"DexScript {__version__}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DexScript(bot))

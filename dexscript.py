import base64
import enum
import logging
import os
import re

import discord
import requests
from difflib import get_close_matches
from discord.ext import commands
from fastapi_admin.resources import Field, Resource

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
    from ballsdex.core.admin.resources import app
    from ballsdex.core.models import Ball, Regime
    from ballsdex.packages.admin.cog import save_file
    from ballsdex.settings import settings
else:
    from carfigures.core.admin.resources import app
    from carfigures.core.models import Car as Ball
    from carfigures.core.models import CarType as Regime
    from carfigures.packages.superuser.cog import save_file
    from carfigures.settings import settings


log = logging.getLogger(f"{dir_type}.core.dexscript")

__version__ = "0.3"


START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
ENABLE_VERSION_WARNING = False

METHODS = [
    "CREATE",
    "UPDATE",
    "REMOVE",
    "DISPLAY",
    "LIST",
]


class TOKENS(enum.Enum):
    METHOD = "METHOD"
    NUMBER = "NUMBER"
    STRING = "STRING"


class DexScriptError(Exception):
    def __init__(self, message):
        self.message = message


class DexScriptParser():
    """
    This class is used to parse DexScript contents into Python code.
    This was ported over from DotZZ's DexScript Migrations JavaScript file.
    """

    def __init__(self, ctx: commands.Context, code: str):
        self.code = code
        self.fields = []
        self.ctx = ctx

    def format_class(self, field):
        """
        Returns a class's identifier. 
        If a token is attached to the class, it will exclude the token.

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
            The string from which you want to grab the token.
        """

        token = TOKENS.STRING

        if self.format_class(line) in METHODS:
            token = TOKENS.METHOD
        elif isinstance(line, (int, float)):
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
        if "\n" not in code:
            code = "\n" + code

        code = code.encode("UTF-8")

        parsed_code = []

        for line1 in code.decode("UTF-8").split("\n"):
            print(line1)

            if line1.startswith("//") or line1 == "":
                continue

            for line2 in line1.split(" > "):
                self.fields.append(self.grab_token(line2.replace("    ", "")))

            parsed_code.append(self.parse_code())

        print(parsed_code)

        return parsed_code

    async def autocorrect_model(self, string, model):
        autocorrection = get_close_matches(string, [x.country for x in await Ball.all()])

        if autocorrection == []:
            raise DexScriptError(f"'{string}' does not exist.")

        if autocorrection[0] != string:
            raise DexScriptError(
                f"'{string}' does not exist.\n"
                f"Did you mean '{autocorrection[0]}'?"
            )

        return autocorrection[0]

    async def get_model(self, model, identifier):
        return_model = None
        new_identity = await self.autocorrect_model(identifier, model)
        
        if dir_type == "ballsdex":
            return_model = await Ball.get(country=new_identity)
        else:
            return_model = await Ball.get(full_name=new_identity)

        return return_model

    async def create_model(self, model, identifier):
        return_model = None

        if dir_type == "ballsdex":
            return_model = await Ball.create(
                country = identifier,
                health = 0,
                attack = 0,
                rarity = 0,
                regime = await Regime.get(name="Democracy"),
                emoji_id = 100 ** 8,
                wild_card = "",
                collection_card = "",
                credits = "DexScript",
                capacity_name = "New Ball",
                capacity_description = "Update this ball by using the UPDATE command."
            )
        else:
            return_model = await Ball.create(
                full_name = identifier,
                weight = 0,
                horsepower = 0,
                cartype = await Regime.get(name="Union"),
                emoji_id = 100 ** 8,
                spawn_picture = "",
                collection_picture = "",
                image_credits = "DexScript",
                car_suggester = "",
                capacity_name = "New Ball",
                capacity_description = "Update this ball by using the UPDATE command."
            )

        return return_model

    async def execute(self, key, item, model):
        formatted_ball = item[model]

        match key:
            case "CREATE":
                new_creation = await self.create_model(model, formatted_ball[1])

                await self.ctx.send(
                    f"Created `{formatted_ball[1]}`\n"
                    f"-# Use the `UPDATE` command to update this {model.lower()}."
                )

            case "UPDATE":
                returned_model = await self.get_model(model, formatted_ball[1])

                new_attribute = None

                if (
                    self.ctx.message.attachments != [] and 
                    hasattr(returned_model, formatted_ball[2].lower())
                ):
                    image_path = await save_file(self.ctx.message.attachments[0])
                    new_attribute = "/" + str(image_path)

                setattr(
                    returned_model, 
                    formatted_ball[2].lower(), 
                    formatted_ball[3] if new_attribute is None else new_attribute
                )

                await returned_model.save()

                await self.ctx.send(
                    f"Updated `{formatted_ball[1]}'s` {formatted_ball[2]}"
                )

            case "REMOVE":
                returned_model = await self.get_model(model, formatted_ball[1])

                await returned_model.delete()

                await self.ctx.send(f"Deleted `{formatted_ball[1]}`")

            case "DISPLAY":
                returned_model = await self.get_model(model, formatted_ball[1])

                #if formatted_ball[2] == "-ALL":
                    #pass

                attribute = getattr(returned_model, formatted_ball[2].lower())

                if os.path.isfile(attribute[1:]):
                    await self.ctx.send(
                        f"```{attribute}```", file=discord.File(attribute[1:])
                    )
                    return

                await self.ctx.send(
                    f"```{getattr(returned_model, formatted_ball[2].lower())}```"
                )

            case "LIST":
                selected_resource: type[Resource] = [
                    x for x in app.resources if x.__name__ == model.title() + "Resource"
                ][0]

                parameters = f"{model} FIELDS:\n\n"

                for field in selected_resource.fields:
                    if not isinstance(field, str) and not isinstance(field, Field):
                        continue

                    label = field if not isinstance(field, Field) else field.label

                    parameters += f"- {label.replace(' ', '_').upper()}\n"

                await self.ctx.send(f"```\n{parameters}\n```")

    async def run(self):
        code_fields = self.parse(self.code)

        if code_fields == {}:
            method = f"{self.code.split(' > ')[0]}"
            raise DexScriptError(f"`{method}` is not a valid command")

        for item in code_fields:
            for key, field in item.items():
                print(key, field)
                await self.execute(key, field, "BALL")


class DexScript(commands.Cog):
    """
    DexScript support
    """

    def __init__(self, bot):
        self.bot = bot

    # TODO: Migrate this function to the utility path 
    # so there aren't any duplicates.
    @staticmethod
    def cleanup_code(content): 
        """
        Automatically removes code blocks from the code.
        """

        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        return content.strip("` \n")

    @staticmethod
    def check_version():
        if not ENABLE_VERSION_WARNING:
            return None

        r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/version.txt")

        if r.status_code != requests.codes.ok:
            return

        new_version = base64.b64decode(r.json()["content"]).decode("UTF-8").rstrip()

        if new_version != __version__:
            return (
                f"Your DexScript version ({__version__}) is outdated. " 
                f"Please update to version {new_version} "
                f"using `{settings.prefix}update-ds`."
            )

        return None

    @commands.command()
    @commands.is_owner()
    async def run(self, ctx: commands.Context, *, code: str):
        """
        Executes DexScript code.
        """

        body = self.cleanup_code(code)

        version_check = self.check_version()

        if version_check:
            await ctx.send(f"-# {version_check}")

        try:
            dexscript_instance = DexScriptParser(ctx, body)
            await dexscript_instance.run()
        except Exception as error:
            await ctx.send(f"```ERROR: \n\n{error}\n```")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def about(self, ctx: commands.Context):
        embed = discord.Embed(
            title="DexScript - ALPHA",
            description=(
                "DexScript is a set of commands created by DotZZ "
                "that allows you to easily "
                "modify, delete, and display data about balls.\n\n"
                "For a guide on how to use DexScript, "
                "refer to the guide on the [DexScript GitHub Page](<https://github.com/Dotsian/DexScript>)"
            ),
            color = discord.Color.from_str("#03BAFC")
        )

        value = ""

        for method in METHODS:
            value += f"* {method}\n"

        embed.add_field(name = "Commands", value=value, inline=False)

        version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

        embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
        embed.set_footer(text=f"DexScript {__version__} ({version_check})")

        await ctx.send(embed=embed)

    @commands.command(name="update-ds")
    @commands.is_owner()
    async def update_ds(self, ctx: commands.Context):
        r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/installer.py")

        if r.status_code == requests.codes.ok:
            content = base64.b64decode(r.json()["content"])
            await ctx.invoke(self.bot.get_command("eval"), body=content.decode("UTF-8"))
        else:
            await ctx.send(
                "Failed to update DexScript.\n"
                "Report this issue to `dot_zz` on Discord."
            )


async def setup(bot):
    await bot.add_cog(DexScript(bot))

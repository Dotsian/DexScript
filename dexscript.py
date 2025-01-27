import base64
import inspect
import logging
import os
import re
import shutil
import traceback
from dataclasses import dataclass
from dataclasses import field as datafield
from difflib import get_close_matches
from enum import Enum
from pathlib import Path
from typing import Any

import discord
import requests
from dateutil.parser import parse as parse_date
from discord.ext import commands

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
    from ballsdex.core.models import Ball, Economy, Regime, Special
    from ballsdex.settings import settings
else:
    from carfigures.core.models import Car as Ball
    from carfigures.core.models import CarType as Regime
    from carfigures.core.models import Country as Economy
    from carfigures.core.models import Event as Special
    from carfigures.settings import settings


log = logging.getLogger(f"{dir_type}.core.dexscript")

__version__ = "0.4.3.3"


START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

MODELS = {
    "ball": Ball,
    "regime": Regime,
    "economy": Economy,
    "special": Special,
}

SETTINGS = {
    "DEBUG": False,
    "OUTDATED-WARNING": True,
    "REFERENCE": "main",
}


class Types(Enum):
    METHOD = 0
    NUMBER = 1
    STRING = 2
    BOOLEAN = 3
    MODEL = 4
    DATETIME = 5


class DexScriptError(Exception):
    pass


# Ported from the Ballsdex admin package.
async def save_file(attachment: discord.Attachment) -> Path:
    path = Path(f"./static/uploads/{attachment.filename}")
    match = FILENAME_RE.match(attachment.filename)

    if not match:
        raise TypeError("The file you uploaded lacks an extension.")
    
    i = 1

    while path.exists():
        path = Path(f"./static/uploads/{match.group(1)}-{i}{match.group(2)}")
        i = i + 1
    
    await attachment.save(path)
    return path


def in_list(list_attempt, index):
    try:
        list_attempt[index]
        return True
    except Exception:
        return False


@dataclass
class Value:
    name: Any
    type: Types
    extra_data: list = datafield(default_factory=list)

    def __str__(self):
        return str(self.name)


class Methods:
    def __init__(self, parser):
        self.parser = parser


    async def help(self, ctx):
        """
        Lists all DexScript commands and provides documentation for them.

        Documentation
        -------------
        HELP
        """
        # getattr(Methods, command).__doc__.replace("\n", "").split("Documentation-------------")
        pass


    async def create(self, ctx, model, identifier):
        """
        Creates a model instance.

        Documentation
        -------------
        CREATE > MODEL > IDENTIFIER
        """
        await self.parser.create_model(model.name, identifier)

        await ctx.send(f"Created `{identifier}`")


    async def delete(self, ctx, model, identifier):
        """
        Deletes a model instance.

        Documentation
        -------------
        DELETE > MODEL > IDENTIFIER
        """
        await self.parser.get_model(model, identifier.name).delete()

        await ctx.send(f"Deleted `{identifier}`")


    async def update(self, ctx, model, identifier, attribute, value):
        """
        Updates a model instance's attribute.

        Documentation
        -------------
        UPDATE > MODEL > IDENTIFIER > ATTRIBUTE > VALUE
        """
        new_attribute = None

        if ctx.message.attachments != []:
            image_path = await save_file(ctx.message.attachments[0])
            new_attribute = Value(f"/{image_path}", Types.STRING)
        else:
            new_attribute = value

        await self.parser.get_model(model, identifier.name).update(
            **{attribute.name.lower(): new_attribute.name}
        )

        await ctx.send(f"Updated `{identifier}'s` {attribute} to `{new_attribute.name}`")


    async def view(self, ctx, model, identifier, attribute=None):
        """
        Displays an attribute of a model instance. If `ATTRIBUTE` is left blank, 
        it will display every attribute of that model instance.

        Documentation
        -------------
        VIEW > MODEL > IDENTIFIER > ATTRIBUTE(?)
        """
        returned_model = await self.parser.get_model(model, identifier.name)

        if attribute is None:
            fields = {"content": "```"}

            for key, value in vars(returned_model).items():
                if key.startswith("_"):
                    continue

                fields["content"] += f"{key}: {value}\n"

                if isinstance(value, str) and value.startswith("/static"):
                    if fields.get("files") is None:
                        fields["files"] = []
                    
                    fields["files"].append(discord.File(value[1:]))

            fields["content"] += "```"

            await ctx.send(**fields)
            return

        new_attribute = getattr(returned_model, attribute.name.lower())

        if isinstance(new_attribute, str) and os.path.isfile(new_attribute[1:]):
            await ctx.send(f"```{new_attribute}```", file=discord.File(new_attribute[1:]))
            return

        await ctx.send(f"```{new_attribute}```")


    async def filter_update(
        self, ctx, model, attribute, old_value, new_value, tortoise_operator=None
    ):
        """
        Updates all instances of a model to the specified value where the specified attribute 
        meets the condition  defined by the optional `TORTOISE_OPERATOR` argument 
        (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER_UPDATE > MODEL > ATTRIBUTE > OLD_VALUE > NEW_VALUE > TORTOISE_OPERATOR(?)
        """
        lower_name = attribute.name.lower()

        if tortoise_operator is not None:
            lower_name += f"__{tortoise_operator.name.lower()}"

        await model.name.filter(**{lower_name: old_value.name}).update(
            **{lower_name: new_value.name}
        )

        await ctx.send(
            f"Updated all `{model}` instances from a "
            f"`{attribute}` value of `{old_value}` to `{new_value}`"
        )


    async def filter_delete(
        self, ctx, model, attribute, value, tortoise_operator=None
    ):
        """
        Deletes all instances of a model where the specified attribute meets the condition 
        defined by the optional `TORTOISE_OPERATOR` argument (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER_DELETE > MODEL > ATTRIBUTE > VALUE > TORTOISE_OPERATOR(?)
        """
        lower_name = attribute.name.lower()
        
        if tortoise_operator is not None:
            lower_name += f"__{tortoise_operator.name.lower()}"
        
        await model.name.filter(**{lower_name: value.name}).delete()

        await ctx.send(
            f"Deleted all `{model}` instances with a "
            f"`{attribute}` value of `{value}`"
        )


    async def attributes(self, ctx, model):
        """
        Lists all changeable attributes of a model.

        Documentation
        -------------
        ATTRIBUTES > MODEL
        """
        model_name = (
            model.name if isinstance(model.name, str) else model.name.__name__
        )

        parameters = f"{model_name.upper()} ATTRIBUTES:\n\n"

        for field in vars(model.name()):  # type: ignore
            if field[:1] == "_":
                continue

            parameters += f"- {field.replace(' ', '_').upper()}\n"

        await ctx.send(f"```{parameters}```")


    async def dev(self, ctx, operation, file_name=None):
        """
        Developer commands for managing and modifying the bot's internal filesystem.

        Documentation
        -------------
        DEV > OPERATION > FILE_NAME(?)
        """
        match operation.name.lower():
            case "write":
                if file_name is None:
                    raise DexScriptError("`File name is None")
                
                new_file = ctx.message.attachments[0]

                with open(file_name.name, "w") as opened_file:
                    contents = await new_file.read()
                    opened_file.write(contents.decode("utf-8"))

                await ctx.send(f"Wrote to `{file_name}`")

            case "clear":
                with open(file_name.name, "w") as _:
                    pass

                await ctx.send(f"Cleared `{file_name}`")

            case "read":
                await ctx.send(file=discord.File(file_name.name))

            case "listdir":
                await ctx.send(f"```{'\n'.join(os.listdir(file_name))}```")

            case "delete":
                is_dir = os.path.isdir(file_name.name)

                file_type = "directory" if is_dir else "file"

                if is_dir:
                    shutil.rmtree(file_name.name)
                else:
                    os.remove(file_name.name)

                await ctx.send(f"Deleted `{file_name}` {file_type}")

            case _:
                raise DexScriptError(
                    f"'{operation}' is not a valid dev operation. "
                    "(READ, WRITE, CLEAR, LISTDIR, or DELETE)"
                )


class DexScriptParser:
    """
    This class is used to parse DexScript into Python code.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.values = []

    @staticmethod
    def is_number(string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_date(string):
        try:
            parse_date(string)
            return True
        except Exception:
            return False

    @staticmethod
    def autocorrect(string, correction_list, error="does not exist."):
        autocorrection = get_close_matches(string, correction_list)

        if not autocorrection or autocorrection[0] != string:
            suggestion = f"\nDid you mean '{autocorrection[0]}'?" if autocorrection else ""

            raise DexScriptError(f"'{string}' {error}{suggestion}")

        return autocorrection[0]
    
    @staticmethod
    def extract_str_attr(object):
        expression = r"return\s+self\.(\w+)"

        return re.search(expression, inspect.getsource(object.__str__)).group(1)

    async def create_model(self, model, identifier):
        fields = {}

        for key, field in vars(model()).items():
            if field is not None:
                continue

            if key in ["id", "short_name"]:
                continue

            fields[key] = 1

            if key in ["country", "full_name", "catch_names", "name"]:
                fields[key] = identifier
            elif key == "emoji_id":
                fields[key] = 100 ** 8
            elif key == "regime_id":
                first_regime = await Regime.first()
                fields[key] = first_regime.pk

        await model.create(**fields)

    async def get_model(self, model, identifier):
        attribute = self.extract_str_attr(model.name)

        correction_list = await model.name.all().values_list(attribute, flat=True)
        translated_identifier = self.translate(model.extra_data[0].lower())

        try:
            returned_model = await model.name.filter(
                **{
                    translated_identifier: self.autocorrect(identifier, correction_list)
                }
            )
        except AttributeError:
            raise DexScriptError(f"'{model}' is not a valid model.")

        return returned_model[0]

    def var(self, value):
        return_value = value

        match value.type:
            case Types.MODEL:
                current_model = MODELS[value.name.lower()]

                string_key = self.extract_str_attr(current_model)

                value.name = current_model
                value.extra_data.append(string_key)

            case Types.BOOLEAN:
                value.name = value.name.lower() == "true"

            case Types.DATETIME:
                value.name = parse_date(value.name)

        return return_value

    @staticmethod
    def translate(string: str, item=None):
        """
        Translates model and field names into a format for both Ballsdex and CarFigures.

        Parameters
        ----------
        string: str
          The string you want to translate.
        """
        if dir_type == "ballsdex":
            return getattr(item, string) if item else string

        translation = {"BALL": "ENTITY", "COUNTRY": "full_name"}

        translated_string = translation.get(string.upper(), string)

        return getattr(item, translated_string) if item else translated_string

    def create_value(self, line):
        type = Types.STRING

        value = Value(line, type)
        lower = line.lower()

        method_functions = [x for x in dir(Methods) if not x.startswith("__")]

        if lower in method_functions:
            type = Types.METHOD
        elif lower in MODELS:
            type = Types.MODEL
        elif self.is_date(lower) and lower.count("-") >= 2:
            type = Types.DATETIME
        elif self.is_number(lower):
            type = Types.NUMBER
        elif lower in ["true", "false"]:
            type = Types.BOOLEAN

        value.type = type

        return self.var(value)

    async def execute(self, code: str) -> str | None:
        try:
            seperator = "\n" if "\n" in code else ";'"

            split_code = [x for x in code.split(seperator) if x.strip() != ""]

            parsed_code: list[list[Value]] = []

            for line in split_code:
                line_code: list[Value] = []
                full_line = ""

                for index2, char in enumerate(line):
                    if char == "":
                        continue

                    full_line += char

                    if full_line == "--":
                        break

                    if char in [">"] or index2 == len(line) - 1:
                        line_code.append(self.create_value(full_line.replace(">", "").strip()))

                        full_line = ""

                        if len(line_code) == len(line.split(">")):
                            parsed_code.append(line_code)

            for line2 in parsed_code:
                method = line2[0]

                if method.type != Types.METHOD:
                    return f"'{method.name}' is not a valid command."
                
                method_function = getattr(Methods(self), method.name.lower())

                line2.pop(0)

                try:
                    await method_function(self.ctx, *line2)
                except TypeError:
                    final = traceback.format_exc()

                    if not SETTINGS["DEBUG"]:
                        final = f"Argument missing when calling {method.name}."

                    return final
        except Exception as error:
            return traceback.format_exc() if SETTINGS["DEBUG"] else error

        return None


class DexScript(commands.Cog):
    """
    DexScript commands
    """

    def __init__(self, bot):
        self.bot = bot

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
        if not SETTINGS["OUTDATED-WARNING"]:
            return None

        r = requests.get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/pyproject.toml",
            {"ref": SETTINGS["REFERENCE"]},
        )

        if r.status_code != requests.codes.ok:
            return

        toml_content = base64.b64decode(r.json()["content"]).decode("UTF-8")
        new_version = re.search(r'version\s*=\s*"(.*?)"', toml_content).group(1)

        if new_version != __version__:
            return (
                f"Your DexScript version ({__version__}) is outdated. "
                f"Please update to version ({new_version}) "
                f"using `{settings.prefix}update-ds`."
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
        body = self.cleanup_code(code)

        version_check = self.check_version()

        if version_check:
            await ctx.send(f"-# {version_check}")

        dexscript_instance = DexScriptParser(ctx)
        result = await dexscript_instance.execute(body)

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
        embed = discord.Embed(
            title="DexScript - BETA",
            description=(
                "DexScript is a set of commands created by DotZZ "
                "that allows you to easily "
                "modify, delete, and display data for models.\n\n"
                "For a guide on how to use DexScript, "
                "refer to the official [DexScript guide](<https://github.com/Dotsian/DexScript/wiki/Commands>).\n\n"
                "If you want to follow DexScript, "
                "join the official [DexScript Discord](<https://discord.gg/EhCxuNQfzt>) server."
            ),
            color=discord.Color.from_str("#03BAFC"),
        )

        version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

        embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
        embed.set_footer(text=f"DexScript {__version__} ({version_check})")

        await ctx.send(embed=embed)

    @commands.command(name="update-ds")
    @commands.is_owner()
    async def update_ds(self, ctx: commands.Context):
        """
        Updates DexScript to the latest version.
        """
        r = requests.get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/installer.py",
            {"ref": SETTINGS["REFERENCE"]},
        )

        if r.status_code == requests.codes.ok:
            content = base64.b64decode(r.json()["content"])
            await ctx.invoke(self.bot.get_command("eval"), body=content.decode("UTF-8"))
        else:
            await ctx.send(
                "Failed to update DexScript. Report this issue to `dot_zz` on Discord.\n"
                f"```ERROR CODE: {r.status_code}```"
            )

    @commands.command(name="reload-ds")
    @commands.is_owner()
    async def reload_ds(self, ctx: commands.Context):
        """
        Reloads DexScript.
        """
        await self.bot.reload_extension(f"{dir_type}.core.dexscript")
        await ctx.send("Reloaded DexScript")

    @commands.command()
    @commands.is_owner()
    async def setting(self, ctx: commands.Context, setting: str, value: str):
        """
        Changes a setting based on the value provided.

        Parameters
        ----------
        setting: str
          The setting you want to toggle.
        value: str
          The value you want to set the setting to.
        """
        response = f"`{setting}` is not a valid setting."

        if setting in SETTINGS:
            selected_setting = SETTINGS[setting]

            if isinstance(selected_setting, bool):
                SETTINGS[setting] = bool(value)
            elif isinstance(selected_setting, str):
                SETTINGS[setting] = value

            response = f"`{setting}` has been set to `{value}`"

        await ctx.send(response)


async def setup(bot):
    await bot.add_cog(DexScript(bot))

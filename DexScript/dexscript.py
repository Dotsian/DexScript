import asyncio
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

DIR = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if DIR == "ballsdex":
    from ballsdex.core.models import Ball, Economy, Regime, Special # noqa: F401, I001
    from ballsdex.settings import settings
else:
    from carfigures.core.models import Car, CarType, Country, Event, FontsPack # noqa: F401, I001
    from carfigures.settings import settings


log = logging.getLogger(f"{DIR}.core.dexscript")

__version__ = "0.5"


START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

MEDIA_PATH = "./admin_panel/media" if os.path.isdir("./admin_panel.media") else "./static/uploads"


class Types(Enum):
    METHOD = 0
    METHOD_EXT = 1
    BOOLEAN = 2
    MODEL = 3
    DATETIME = 4


class DexScriptError(Exception):
    pass


async def save_file(attachment: discord.Attachment) -> Path:
    path = Path(f"{MEDIA_PATH}/{attachment.filename}")
    match = FILENAME_RE.match(attachment.filename)

    if not match:
        raise TypeError("The file you uploaded lacks an extension.")
    
    i = 1

    while path.exists():
        path = Path(f"{MEDIA_PATH}/{match.group(1)}-{i}{match.group(2)}")
        i = i + 1
    
    await attachment.save(path)
    return path


@dataclass
class Value:
    name: Any
    type: Types = Types.DEFAULT
    extra_data: list = datafield(default_factory=list)

    def __str__(self):
        return str(self.name)


@dataclass
class Settings:
    """
    Settings class for DexScript.
    """

    debug: bool = False
    versioncheck: bool = False
    reference: str = "main"


config = Settings()


@dataclass
class Models:
    """
    Model functions.
    """

    @staticmethod
    def fetch_model(field):
        return globals().get(field)

    @staticmethod
    def all(names=False, key=None):
        allowed_list = {
            "ballsdex": [
                "Ball",
                "Regime",
                "Economy",
                "Special"
            ],
            "carfigures": [
                "Car",
                "CarType",
                "Country",
                "Event",
                "FontsPack"
            ]
        }

        return_list = allowed_list[DIR]

        if not names:
            return_list = [globals().get(x) for x in return_list if globals().get(x) is not None]

        if key is not None:
            return_list = [key(x) for x in return_list]

        return return_list

    

    @staticmethod
    def port(original: str | list[str]):
        """
        Translates model and field names into a format for both Ballsdex and CarFigures.

        Parameters
        ----------
        original: str | list[str]
            The original string or list of strings you want to translate.
        """
        if DIR == "ballsdex":
            return original

        translation = {
            "BALL": "ENTITY",
            "COUNTRY": "fullName",
            "SHORT_NAME": "shortName",
            "CATCH_NAMES": "catchNames",
            "ICON": "image",
        }

        if isinstance(original, list):
            translated_copy = [translation.get(x.upper(), x) for x in original]
        else:
            translated_copy = translation.get(original.upper(), original)

        return translated_copy


@dataclass
class Utils:
    """
    DexScript utility functions.
    """

    @staticmethod
    def remove_code_markdown(content) -> str:
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        return content.strip("` \n")

    @static_method
    def is_image(path) -> bool:
        if path.startswith("/static/uploads"):
            path.replace("/static/uploads/", "")
        
        return os.path.isfile(f"{MEDIA_PATH}/{path}")

    @staticmethod
    def is_date(string) -> bool:
        try:
            parse_date(string)
            return True
        except Exception:
            return False


@dataclass
class IncludeParser:
    parser: Any

@dataclass
class Methods(IncludeParser):
    """
    Main methods for DexScript.
    """

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


    async def update(self, ctx, model, identifier, attribute, value=None):
        """
        Updates a model instance's attribute. If value is None, it will check
        for any attachments.

        Documentation
        -------------
        UPDATE > MODEL > IDENTIFIER > ATTRIBUTE > VALUE(?)
        """
        new_attribute = value

        if value is None and self.parser.attachments != []:
            image_path = await save_file(self.parser.attachments[0])
            new_attribute = Value(f"/{image_path}")

            self.parser.attachments.pop(0)

        # models_list = Models.all(True)

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

                if isinstance(value, str) and Utils.is_image(value):
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


    class Filter:
        """
        Filter commands used for mass updating, deleting, and viewing models.
        """

        # TODO: Add attachment support.
        async def update(
            self, ctx, model, attribute, old_value, new_value, tortoise_operator=None
        ):
            """
            Updates all instances of a model to the specified value where the specified attribute 
            meets the condition  defined by the optional `TORTOISE_OPERATOR` argument 
            (e.g., greater than, equal to, etc.).

            Documentation
            -------------
            FILTER > UPDATE > MODEL > ATTRIBUTE > OLD_VALUE > NEW_VALUE > TORTOISE_OPERATOR(?)
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

        def delete(
            self, ctx, model, attribute, value, tortoise_operator=None
        ):
            """
            Deletes all instances of a model where the specified attribute meets the condition 
            defined by the optional `TORTOISE_OPERATOR` argument 
            (e.g., greater than, equal to, etc.).

            Documentation
            -------------
            FILTER > DELETE > MODEL > ATTRIBUTE > VALUE > TORTOISE_OPERATOR(?)
            """
            lower_name = attribute.name.lower()
            
            if tortoise_operator is not None:
                lower_name += f"__{tortoise_operator.name.lower()}"
            
            await model.name.filter(**{lower_name: value.name}).delete()

            await ctx.send(
                f"Deleted all `{model}` instances with a "
                f"`{attribute}` value of `{value}`"
            )


    class Eval:
        """
        Developer commands for executing evals.
        """

        def __loaded__(self):
            os.makedirs("eval_presets", exist_ok=True)


        async def exec_git(self, ctx, link):
            link = link.split("/")
            api = f"https://api.github.com/repos/{link[0]}/{link[1]}/contents/{link[2]}"
            
            request = requests.get(api)

            if request.status_code != requests.codes.ok:
                raise DexScriptError(f"Request Error Code {request.status_code}")

            content = base64.b64decode(r.json()["content"])

            try:
                await ctx.invoke(bot.get_command("eval"), body=content.decode("UTF-8"))
            except Exception as error:
                raise DexScriptError(error)
            else:
                await ctx.message.add_reaction("✅")
                

        async def save(self, ctx, name):
            if len(name) > 25:
                raise DexScriptError(f"`{name}` is above the 25 character limit.")
            
            if os.path.isfile(f"eval_presets/{name}.py"):
                raise DexScriptError(f"`{name}` aleady exists.")

            save_content = ""

            await ctx.send("Please paste the eval command below...")

            try:
                message = await bot.wait_for(
                    "message", timeout=15, check=lambda m: m.author == ctx.message.author
                )
            except asyncio.TimeoutError:
                await channel.send("Preset saving has timed out.")
                return
            with open(f"eval_presets/{name}.py", "w") as file:
                file.write(Utils.remove_code_markdown(message.content))

            await ctx.send(f"`{name}` eval preset has been saved!")


        async def remove(self, ctx, name):
            if not os.path.isfile(f"eval_presets/{name}.py"):
                raise DexScriptError(f"`{name}` does not exists.")

            os.remove(f"eval_presets/{name}.py")

            await ctx.send(f"Removed `{name}` preset.")


        async def run(self, ctx, name): # TODO: Allow args to be passed through `run`.
            if not os.path.isfile(f"eval_presets/{name}.py"):
                raise DexScriptError(f"`{name}` does not exists.")

            with open(f"eval_presets/{name}.py", "r") as file:
                try:
                    await ctx.invoke(bot.get_command("eval"), body=file.read())
                except Exception as error:
                    raise DexScriptError(error)
                else:
                    await ctx.message.add_reaction("✅")


    class File:
        """
        Developer commands for managing and modifying the bot's internal filesystem.
        """

        async def read(self, ctx, file_path):
            await ctx.send(file=discord.File(file_path.name))

                
        async def write(self, ctx, file_path):
            new_file = ctx.message.attachments[0]

            with open(file_path.name, "w") as opened_file:
                contents = await new_file.read()
                opened_file.write(contents.decode("utf-8"))

            await ctx.send(f"Wrote to `{file_path}`")


        async def clear(self, ctx, file_path):
            with open(file_path.name, "w") as _:
                pass

            await ctx.send(f"Cleared `{file_path}`")


        async def listdir(self, ctx, file_path=None):
            path = file_path.name if file_path is not None else None

            await ctx.send(f"```{'\n'.join(os.listdir(path))}```")
            

        async def delete(self, ctx, file_path):
            is_dir = os.path.isdir(file_path.name)

            file_type = "directory" if is_dir else "file"

            if is_dir:
                shutil.rmtree(file_path.name)
            else:
                os.remove(file_path.name)

            await ctx.send(f"Deleted `{file_path}` {file_type}")


class DexScriptParser:
    """
    This class is used to parse DexScript into Python code.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.attachments = ctx.message.attachments
        self.values = []

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

        for field, field_type in model._meta.fields_map.items():
            field_data = vars(model()).get(field)

            special_list = {
                "Identifiers": ["country", "catch_names", "name"],
                "Ignore": ["id", "short_name"]
            }

            for key, value in special_list.items():
                special_list[key] = Models.port(value)

            if field_data is not None or field in special_list["Ignore"]:
                continue

            if key in special_list["Identifiers"]:
                fields[key] = identifier
                continue

            match field_type:
                case "ForeignKeyFieldInstance":
                    fetched_model = Models.fetch_model(field)
                    instance = await fetched_model.first()

                    if instance is None:
                        raise DexScriptError(f"Could not find default {field}")

                    fields[field] = instance.pk

                case "BigIntField":
                    fields[field] = 100 ** 8

                case "BackwardFKRelation" | "JSONField":
                    continue

                case _:
                    fields[field] = 1

        await model.create(**fields)

    async def get_model(self, model, identifier):
        attribute = self.extract_str_attr(model.name)

        correction_list = await model.name.all().values_list(attribute, flat=True)
        translated_identifier = Models.port(model.extra_data[0].lower())

        try:
            returned_model = await model.name.filter(
                **{
                    translated_identifier: self.autocorrect(identifier, correction_list)
                }
            )
        except AttributeError:
            raise DexScriptError(f"'{model}' is not a valid model.")

        return returned_model[0]

    def create_value(self, line):
        value = Value(line)
        lower = line.lower()

        classes = []
        functions = []

        method_items = [x for x in dir(Methods) if not x.startswith("__")]

        for func in method_items:
            if inspect.isclass(getattr(Methods, func)):
                classes.append(func)
                continue
            
            functions.append(func)

        type_dict = {
            Types.METHOD: lower in functions,
            Types.METHOD_EXT: lower in classes,
            Types.MODEL: lower in Models.all(True, key=str.lower),
            Types.DATETIME: Utils.is_date(lower) and lower.count("-") >= 2,
            Types.BOOLEAN: lower in ["true", "false"]
        }

        for key, operation in type_dict.items():
            if operation is False:
                continue

            value.type = key
            break

        match value.type:
            case Types.MODEL:
                model = Models.fetch_model(line)

                string_key = self.extract_str_attr(model)

                value.name = model
                value.extra_data.append(string_key)

            case Types.BOOLEAN:
                value.name = lower == "true"

            case Types.DATETIME:
                value.name = parse_date(value.name)

        return value

    def error(self, message, log):
        return (message, log)[config.debug]

    async def execute(self, code: str):
        loaded_methods = Methods(self)

        split_code = [x for x in code.split("\n") if x.strip() != ""]

        parsed_code = [
            [self.create_value(s.strip()) for s in re.findall(r"[^>]+", line)]
            for line in split_code if not line.strip().startswith("--")
        ]

        for line2 in parsed_code:
            if line2 == []:
                continue
            
            method = line2[0]

            line2.pop(0)

            if method.type != Types.METHOD:
                return self.error(
                    f"'{method.name}' is not a valid command.",
                    traceback.format_exc()
                )

            method_call = getattr(loaded_methods, method.name.lower())

            if line2[0].type == Types.METHOD_EXT:
                method_call = getattr(method_call, line2[1].name.title())
                line2.pop(0)

            try:
                await method_call(self.ctx, *line2)
            except TypeError:
                return self.error(
                    f"Argument missing when calling '{method.name}'.",
                    traceback.format_exc()
                )


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
            {"ref": config.branch},
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
        body = Utils.remove_code_markdown(code)

        version_check = self.check_version()

        if version_check:
            await ctx.send(f"-# {version_check}")

        dexscript_instance = DexScriptParser(ctx)

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
            f"about DexScript's functionality or use the `{settings.prefix}.run HELP` to display "
            "a list of all commands and what they do.\n\n"
            "If you want to follow DexScript or require assistance, join the official "
            f"[DexScript Discord server](<{discord_link}>)."
        )

        embed = discord.Embed(
            title="DexScript - BETA",
            description=description,
            color=discord.Color.from_str("#03BAFC"),
        )

        embed.add_field(
            name="Updating DexScript",
            value=(
                "To update DexScript, run "
                f"`{settings.prefix}.run EVAL > EXEC_GIT > Dotsian/DexScript/installer.py`"
            )
        )

        version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

        embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
        embed.set_footer(text=f"DexScript {__version__} ({version_check})")

        await ctx.send(embed=embed)

    @commands.command(name="reload-ds")
    @commands.is_owner()
    async def reload_ds(self, ctx: commands.Context):
        """
        Reloads DexScript.
        """
        await self.bot.reload_extension(f"{DIR}.core.dexscript")
        await ctx.send("Reloaded DexScript")

    @commands.command()
    @commands.is_owner()
    async def setting(
        self, ctx: commands.Context, setting: str, value: str | None = None
    ):
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


async def setup(bot):
    await bot.add_cog(DexScript(bot))

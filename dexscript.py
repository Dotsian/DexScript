from base64 import b64decode
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field as datafield
from datetime import datetime
from difflib import get_close_matches
from enum import Enum
from logging import getLogger
from os import mkdir, path
from os import remove as os_remove
from pathlib import Path
from re import compile as recompile
from shutil import rmtree
from time import time
from traceback import format_exc
from typing import Any

from dateutil.parser import parse as parse_date
from discord import Color, Embed
from discord import File as DiscordFile
from discord.ext import commands
from fastapi_admin.app import app
from requests import codes as request_codes
from requests import get as request_get
from tortoise.models import Model as TortoiseModel
from yaml import dump as yaml_dump
from yaml import safe_load as yaml_load

dir_type = "ballsdex" if path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
    from ballsdex.packages.admin.cog import save_file
    from ballsdex.settings import settings
else:
    from carfigures.packages.superuser.cog import save_file
    from carfigures.settings import settings


log = getLogger(f"{dir_type}.core.dexscript")

__version__ = "0.4.4"


START_CODE_BLOCK_RE = recompile(r"^((```sql?)(?=\s)|(```))")

MODELS = {}

KEYWORDS = [
    "local",
    "global",
]

dexclasses = []

dex_globals = {}
dex_yields = []

verified = False


class Types(Enum):
    CLASS = 0
    NUMBER = 1
    STRING = 2
    BOOLEAN = 3
    VARIABLE = 4
    KEYWORD = 5
    MODEL = 6
    DATETIME = 7


class YieldType(Enum):
    CREATE_MODEL = 0


class CodeStatus(Enum):
    SUCCESS = 0
    FAILURE = 1


class DexScriptError(Exception):
    pass


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


@dataclass
class ModelValue:
    model: TortoiseModel
    identifier: str
    fields: dict


@dataclass
class Yield:
    model: Any
    identifier: Any
    value: dict
    type: YieldType

    @staticmethod
    def get(model, identifier):
        return next(
            (x for x in dex_yields if (x.model, x.identifier.name) == (model, identifier)), None
        )


class Package:
    def __init__(self, yml):
        self.__dict__.update(yml)


@dataclass
class Settings:
    debug: bool = False
    outdated_warnings: bool = True
    safe_mode: bool = True
    branch: str = "main"

    @property
    def values(self):
        return vars(self)

    def load(self):
        with open("script-config.yml") as file:
            content = yaml_load(file.read())

            for key, value in content.items():
                setattr(self, key, value)

    def save(self):
        with open("script-config.yml", "w") as file:
            file.write(yaml_dump(self.values))


script_settings = Settings()
script_settings.load()


def script_class(new_class):
    global dexclasses
    dexclasses.append(new_class)

    def new_init(self, ctx):
        self.ctx = ctx

    new_class.__init__ = new_init

    return new_class


class Models:
    """
    Functions used for creating and fetching models.
    """

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

    @staticmethod
    def autocorrect(string, correction_list, error="does not exist."):
        autocorrection = get_close_matches(string, correction_list)

        if not autocorrection or autocorrection[0] != string:
            suggestion = f"\nDid you mean '{autocorrection[0]}'?" if autocorrection else ""

            raise DexScriptError(f"'{string}' {error}{suggestion}")

        return autocorrection[0]

    @staticmethod
    async def all() -> dict:
        models = {}

        for resource in app.resources:
            MODEL = vars(resource).get("model")

            if MODEL is None:
                continue

            fields = {}
            identifier = ""

            for key, instance in MODEL._meta.fields_map.items():
                field_type = instance.__class__.__name__

                fields[key] = field_type

                if field_type in ("CharField", "BigIntField") and identifier == "":
                    identifier = key

            if identifier == "":
                identifier = MODEL._meta.pk_attr

            models[MODEL.__name__.lower()] = ModelValue(MODEL, identifier, fields)

        return models

    @staticmethod
    async def create(model, identifier, yield_creation=False) -> TortoiseModel | Yield:
        fields = {}
        model_data = MODELS[model.__name__.lower()]

        for field, field_type in model_data.fields.items():
            field_data = vars(model())[field]

            if field_data is not None or field in ["id", "short_name"]:
                continue

            if field == model_data.identifier:
                fields[field] = identifier
                continue

            match field_type:
                case "ForeignKeyFieldInstance":
                    first_model = await MODELS[field].model.first()

                    if first_model is None:
                        raise DexScriptError(f"Could not find {field}")

                    fields[field] = first_model.pk

                case "BigIntField":
                    fields[field] = 100**8

                case "BackwardFKRelation" | "JSONField":
                    continue

                case _:
                    fields[field] = 1

        if yield_creation:
            return Yield(model, identifier, fields, YieldType.CREATE_MODEL)

        return await model.create(**fields)

    @staticmethod
    async def get(model, identifier):
        try:
            returned_model = await model.name.filter(
                **{
                    Models.translate(model.extra_data[0].lower()): Models.autocorrect(
                        identifier, [str(x) for x in await model.name.all()]
                    )
                }
            )
        except AttributeError:
            raise DexScriptError(f"{model} is not a valid model.")

        return returned_model[0]

    @staticmethod
    async def delete(model, identifier):
        returned_model = await Models.get(model, identifier)

        await returned_model.delete()


MODELS = Models.all()


class DexClasses:
    """
    Classes used for DexScript's parser.
    """

    class Model:
        async def push(self, action: str = ""):
            global dex_yields

            if action == "-clear":
                dex_yields = []

                await self.ctx.send("Cleared yield cache.")
                return

            for index, yield_object in enumerate(dex_yields, start=1):
                if action != "" and int(action) >= index:
                    break

                match yield_object.type:
                    case YieldType.CREATE_MODEL:
                        await yield_object.model.create(**yield_object.value)

            plural = "" if len(dex_yields) == 1 else "s"
            number = action if action != "" else len(dex_yields)

            await self.ctx.send(f"Pushed `{number}` yield{plural}.")

            dex_yields = []

        async def create(self, model: TortoiseModel, identifier: str, create_yield: bool = False):
            new_model = await Models.create(model, identifier, create_yield or False)
            suffix = ""

            if isinstance(new_model, Yield):
                suffix = "and yielded it until `push`"
                dex_yields.append(new_model)

            await self.ctx.send(f"Created `{identifier}` {suffix}")

        async def update(
            self, model: TortoiseModel, identifier: str, field: str, value: Any = None
        ):
            found_yield = Yield.get(model, identifier)

            if value is None and self.ctx.message.attachments != []:
                image_path = await save_file(self.ctx.message.attachments[0])
                value = Value(f"/{image_path}", Types.STRING)

            update_message = f"`{identifier}'s` {field} to `{value.name}`"

            if found_yield is None:
                model = await Models.get(model, identifier)
                field = field.lower()

                if not hasattr(model, field):
                    raise DexScriptError(f"{str(model).upper()} has no field '{field}'")

                setattr(model, field, value.name)

                await model.save()

                await self.ctx.send(f"Updated {update_message}")
                return

            found_yield.value[field] = value.name

            await self.ctx.send(f"Updated yielded {update_message}")

        async def view(self, model: TortoiseModel, identifier: str, field: str = ""):
            model = await Models.get(model, identifier)

            if field == "":
                fields: dict = {"content": "```"}

                for key, value in vars(model).items():
                    if key.startswith("_"):
                        continue

                    fields["content"] += f"{key}: {value}\n"

                    if isinstance(value, str) and value.startswith("/static"):
                        if fields.get("files") is None:
                            fields["files"] = []
                        fields["files"].append(DiscordFile(value[1:]))

                fields["content"] += "```"

                await self.ctx.send(**fields)
                return

            attribute = getattr(model, field)

            if isinstance(attribute, str) and path.isfile(attribute[1:]):
                await self.ctx.send(f"```{attribute}```", file=DiscordFile(attribute[1:]))
                return

            await self.ctx.send(f"```{attribute}```")

        async def list(self, model: Any):
            parameters = "GLOBAL YIELDS:\n\n"

            model_name = model if isinstance(model, str) else model.__name__

            if model_name.lower() != "-yields":
                parameters = f"{model_name.upper()} FIELDS:\n\n"

                for field in vars(model()):  # type: ignore
                    if field[:1] == "_":
                        continue

                    parameters += f"- {field.replace(' ', '_').upper()}\n"
            else:
                for index, dex_yield in enumerate(dex_yields, start=1):
                    parameters += f"{index}. {dex_yield.identifier.name.upper()}\n"

            await self.ctx.send(f"```\n{parameters}\n```")

        async def delete(self, model: TortoiseModel, identifier: str):
            await Models.delete(model, identifier)
            await self.ctx.send(f"Deleted `{identifier}`")

    @script_class
    class Ball(Model):
        async def spawn(self, ball: str = "random", amount: int = 1):
            # TODO: Figure out a way to add CF support and BD support.
            for _ in range(amount):
                if ball == "random":
                    pass

            await self.ctx.send("Work in progress...")

    @script_class
    class File:
        async def write(self, file: str):
            new_file = self.ctx.message.attachments[0]

            with open(file, "w") as write_file:
                contents = await new_file.read()
                write_file.write(contents.decode("utf-8"))

            await self.ctx.send(f"Wrote to `{file}`")

        async def read(self, file: str):
            await self.ctx.send(contents=f"Sent `{file}`", file=DiscordFile(file))

        async def clear(self, file: str):
            with open(file, "w") as _:
                pass

            await self.ctx.send(f"Cleared `{file}`")

        async def delete(self, file: str):
            os_remove(file)

            await self.ctx.send(f"Deleted `{file}`")


class DexScriptParser:
    """
    This class is used to parse DexScript into Python code.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.dex_locals = {}
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

    def var(self, value):
        return_value = value

        match value.type:
            case Types.VARIABLE:
                return_value = value

                if value.name in self.dex_locals:
                    return_value = self.dex_locals[value.name]
                elif value.name in dex_globals:
                    return_value = dex_globals[value.name]
                else:
                    raise DexScriptError(f"'{value.name}' is an unknown variable.")

            case Types.MODEL:
                current_model = MODELS[value.name.lower()]

                value.name = current_model.model
                value.extra_data.append(current_model.identifier)

            case Types.BOOLEAN:
                value.name = value.name.lower() == "true"

            case Types.DATETIME:
                value.name = parse_date(value.name)

        return return_value

    def keyword(self, line):
        identity = line[1].name
        value = line[2].name

        match line[0].name.lower():
            case "local":
                self.dex_locals[identity] = value
            case "global":
                dex_globals[identity] = value

    def create_value(self, line):
        type = Types.STRING

        value = Value(line, type)
        lower = line.lower()

        class_names = [x.__name__.lower() for x in dexclasses]

        if lower in class_names:
            type = Types.CLASS
        elif lower in KEYWORDS:
            type = Types.KEYWORD
        elif lower.startswith("$"):
            type = Types.VARIABLE
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

    async def execute(self, code: str):
        try:
            if (seperator := "\n") not in code:
                seperator = "^"

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
                for value in line2:
                    if value.type == Types.KEYWORD:
                        self.keyword(parsed_code)
                        continue

                    if value.type != Types.CLASS:
                        continue

                    new_class = [
                        x for x in dexclasses if x.__name__.lower() == value.name.lower()
                    ][0](self.ctx)

                    new_method = getattr(new_class, line2[1])

                    try:
                        await new_method(*line2.pop(1))
                    except IndexError:
                        error = f"Argument is missing when calling {value.name}."
                        return (error, CodeStatus.FAILURE)
        except Exception as error:
            return ((error, format_exc()), CodeStatus.FAILURE)

        return (None, CodeStatus.SUCCESS)


def fetch_package(name):
    """
    Returns package information based on the name passed.

    Parameters
    ----------
    name: str
        The name of the package you want to return.
    """

    package_path = f"{dir_type}/data/{name}.yml"

    if not path.isfile(package_path):
        return None

    return Package(yaml_load(Path(f"{dir_type}/data/{name}.yml").read_text()))


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
        if not script_settings.outdated_warnings:
            return None

        r = request_get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/version.txt",
            {"ref": script_settings.branch},
        )

        if r.status_code != request_codes.ok:
            return

        new_version = b64decode(r.json()["content"]).decode("UTF-8").rstrip()

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
          The code you'd like to execute.
        """

        body = self.cleanup_code(code)

        version_check = self.check_version()

        if version_check:
            await ctx.send(f"-# {version_check}")

        dexscript_instance = DexScriptParser(ctx)
        result, status = await dexscript_instance.execute(body)

        if status == CodeStatus.FAILURE and result is not None:
            error = result

            if isinstance(error, tuple):
                error = result[int(script_settings.debug)]

            await ctx.send(f"```ERROR: {error}\n```")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def migrate(self, ctx: commands.Context):
        pass

    @commands.command()
    @commands.is_owner()
    async def about(self, ctx: commands.Context, package: str = "DexScript"):
        """
        Displays information about a package.

        Parameters
        ----------
        package: str
            The package you want to view. Default is DexScript.
        """

        if package != "DexScript":
            info = fetch_package(package)

            if info is None:
                await ctx.send("The package you entered does not exist.")
                return

            embed = Embed(
                title=package,
                description=info.description,
            )

            color = info.color if hasattr(info, "color") else "03BAFC"

            embed.color = Color.from_str(f"#{color}")

            if hasattr(info, "logo"):
                embed.set_thumbnail(url=info.logo)

            embed.set_footer(text=f"{package} {info.version}")

            await ctx.send(embed=embed)

            return

        embed = Embed(
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
            color=Color.from_str("#03BAFC"),
        )

        version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

        embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
        embed.set_footer(text=f"DexScript {__version__} ({version_check})")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def uninstall(self, ctx: commands.Context, package: str):
        """
        Uninstalls a package.

        Parameters
        ----------
        package: str
            The package you want to uninstall.
        """

        embed = Embed(
            title=f"Removed {package.title()}",
            description=f"The {package.title()} package has been removed from your bot.",
            color=Color.red(),
            timestamp=datetime.now(),
        )

        rmtree(f"{dir_type}/packages/{package}")

        await bot.unload_extension(f"{dir_type}/packages/{package}")

        await self.bot.tree.sync()

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def verify(self, ctx: commands.Context):
        """
        Verifies you want to install a package.
        """

        global verified

        verified = True

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def install(self, ctx: commands.Context, package: str):
        """
        Installs a package to your Discord bot.

        Parameters
        ----------
        package: str
            The package you want to install.
            It must be a GitHub link with a `package.yml` file.
        """

        global verified

        if not package.startswith("https://github.com/"):
            await ctx.send("The link you sent is not a valid GitHub link.")
            return

        if script_settings.safe_mode and not verified:
            await ctx.send(
                "**CAUTION:** are you sure you want to install this package?\n"
                "All packages you install can modify your Discord bot.\n"
                f"Run the `{settings.prefix}verify` comamnd to verify "
                "you want to install this package.\n"
                "-# To disable this warning, turn off the `safe_mode` setting."
            )

            return

        if verified:
            verified = False

        t1 = time()

        package_info = package.replace("https://github.com/", "").split("/")

        original_name = package_info[1]

        link = f"https://api.github.com/repos/{package_info[0]}/{package_info[1]}/contents/"

        request = request_get(f"{link}package.yml")

        if request.status_code == request_codes.ok:
            content = b64decode(request.json()["content"])

            with open(f"{dir_type}/data/{package_info[1]}.yml", "w") as package_file:
                package_file.write(content.decode("UTF-8"))

            yaml_content = yaml_load(content)
            package_info = Package(yaml_content)

            if dir_type not in package_info.supported:
                await ctx.send(f"This package does not support {dir_type}.")
                return

            color = package_info.color if hasattr(package_info, "color") else "03BAFC"

            embed = Embed(
                title=f"Installing {original_name}",
                description=(
                    f"{original_name} is being installed on your bot.\n"
                    "Please do not turn off your bot."
                ),
                color=Color.from_str(f"#{color}"),
                timestamp=datetime.now(),
            )

            if hasattr(package_info, "logo"):
                embed.set_thumbnail(url=package_info.logo)

            original_message = await ctx.send(embed=embed)
        else:
            await ctx.send(
                f"Failed to install {package_info[1]}.\n"
                f"Report this issue to `{package_info[0]}`.\n"
                f"```ERROR CODE: {request.status_code}```"
            )
            return

        with suppress(FileExistsError):
            mkdir(f"{dir_type}/packages/{package_info.name}")

        for file in package_info.files:
            file_path = f"{package_info.name}/{file}"
            request_content = request_get(f"{link}{file_path}")

            if request_content.status_code == request_codes.ok:
                content = b64decode(request_content.json()["content"])

                with open(f"{dir_type}/packages/{file_path}", "w") as opened_file:
                    opened_file.write(content.decode("UTF-8"))
            else:
                await ctx.send(
                    f"Failed to install the `{file}` file.\n"
                    f"Report this issue to `{package_info.author}`.\n"
                    f"```ERROR CODE: {request_content.status_code}```"
                )

        try:
            await self.bot.load_extension(f"{dir_type}.packages.{package_info.name}")
        except commands.ExtensionAlreadyLoaded:
            await self.bot.reload_extension(f"{dir_type}.packages.{package_info.name}")

        t2 = time()

        embed.title = f"{original_name} Installed"

        embed.description = (
            f"{original_name} has been installed to your bot\n{package_info.description}"
        )

        embed.set_footer(text=f"{original_name} took {round((t2 - t1) * 1000)}ms to install")

        await original_message.edit(embed=embed)

    @commands.command(name="update-ds")
    @commands.is_owner()
    async def update_ds(self, ctx: commands.Context):
        """
        Updates DexScript to the latest version.
        """

        r = request_get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/installer.py",
            {"ref": script_settings.branch},
        )

        if r.status_code == request_codes.ok:
            content = b64decode(r.json()["content"])
            await ctx.invoke(self.bot.get_command("eval"), body=content.decode("UTF-8"))
        else:
            await ctx.send(
                "Failed to update DexScript.\n" "Report this issue to `dot_zz` on Discord."
            )
            print(f"ERROR CODE: {r.status_code}")

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
    async def setting(self, ctx: commands.Context, setting: str, value: str | None = None):
        """
        Changes a setting based on the value provided.

        Parameters
        ----------
        setting: str | None
          The setting you want to edit.
        value: str | None
          The value you want to set the setting to.
        """

        if setting not in script_settings.values:
            await ctx.send(f"`{setting}` is not a valid setting.")
            return

        selected_setting = script_settings.values.get(setting)

        if value is None and not isinstance(selected_setting, bool):
            await ctx.send("You must specify a value for this setting.")
            return

        if value is None and isinstance(selected_setting, bool):
            value = not selected_setting
        elif instance(selected_setting, bool):
            value = bool(value)

        old_value = getattr(script_settings, setting)

        setattr(script_settings, setting, value)

        script_settings.save()

        await ctx.send(f"`{setting}` has been set from `{old_value}` to `{value}`")


async def setup(bot):
    await bot.add_cog(DexScript(bot))

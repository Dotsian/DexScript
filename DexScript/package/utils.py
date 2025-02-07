import asyncio
import contextlib
import inspect
import os
import re
from dataclasses import dataclass
from difflib import get_close_matches
from enum import Enum
from io import StringIO
from pathlib import Path

import discord
from dateutil.parser import parse as parse_date

DIR = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if DIR == "ballsdex":
    from ballsdex.core.models import Ball, Economy, Regime, Special  # noqa: F401, I001
else:
    from carfigures.core.models import Car, CarType, Country, Event, FontsPack  # noqa: F401, I001

START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

MEDIA_PATH = "./admin_panel/media" if os.path.isdir("./admin_panel/media") else "./static/uploads"


class Types(Enum):
    DEFAULT = 0
    METHOD = 1
    CLASS = 2
    BOOLEAN = 3
    MODEL = 4
    DATETIME = 5

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
class Utils:
    """
    Utility functions for DexScript.
    """

    @staticmethod
    def image_path(path) -> bool:
        full_path = path.replace('/static/uploads/', '')

        if MEDIA_PATH == "./static/uploads" and full_path[0] == ".":
            full_path = full_path[1:]

        return f"{MEDIA_PATH}/{full_path}"

    @staticmethod
    def is_image(path) -> bool:
        return os.path.isfile(Utils.image_path(path))

    @staticmethod
    def is_date(string) -> bool:
        try:
            parse_date(string)
            return True
        except Exception:
            return False

    @staticmethod
    def _common_format(string_or_list: str | list[str], func):
        if isinstance(string_or_list, str):
            return func(string_or_list)
        
        return [func(x) for x in string_or_list]

    @staticmethod
    def to_camel_case(item):
        """
        Formats a string or list from snake_case into camelCase for CarFigure support.
        """
        return Utils._common_format(
            item, func=lambda s: re.sub( r"(_[a-z])", lambda m: m.group(1)[1].upper(), s)
        )

    @staticmethod
    def to_pascal_case(item):
        """
        Formats a string or list from snake or camel case to pascal case for class support.
        """
        return Utils._common_format(
            item, func=lambda s: re.sub(
                r"(_[a-z])", lambda m: m.group(1)[1].upper(), s[:1].upper() + s[1:]
            )
        )
    
    @staticmethod
    def to_snake_case(item):
        """
        Formats a string or list from camelCase into snake_case for CarFigure support.
        """
        return Utils._common_format(
            item, func=lambda s: re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()
        )
    
    @staticmethod
    def casing(item, pascal=False):
        """
        Determines whether to use camelCase, snake_case, or pascal case depending on 
        if the bot is using CarFigures or Ballsdex.
        """
        main_casing = Utils.to_snake_case(item)

        if DIR == "carfigures":
            main_casing = Utils.to_camel_case(item)

        if pascal:
            main_casing = Utils.to_pascal_case(item)

        return main_casing

    @staticmethod
    async def message_list(ctx, messages: list[str]):
        """
        Creates an interactive message limit that allows you to display a list of messages 
        without suprassing the Discord message character limit.

        Parameters
        ----------
        ctx: discord.Context
            The context object that will be used.
        messages: list[str]
            The list of messages you want to add to the interaction.
        """
        pages = [[]]
        page_length = 0

        def check(message):
            return (
                message.author.id == ctx.message.author.id and 
                message.content.lower() in ("more", "file")
            )
        
        for message in messages:
            if page_length + len(messages) >= 750:
                page_length = 0
                pages.append([])

            page_length += len(message)
            pages[-1].append(message)

        for index, page in enumerate(pages, start=1):
            await ctx.send(f"```\n{'\n'.join(page)}\n```")

            if index == len(pages):
                break

            remaining = len(pages) - index

            text = f"There are `{remaining}` pages remaining."

            if remaining == 1:
                text = "There is `1` page remaining."

            message = await ctx.send(
                f"{text} Type `more` to continue or `file` to send all messages in a file"
            )

            try:
                response = await ctx.bot.wait_for("message", check=check, timeout=15)
            except asyncio.TimeoutError:
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()

                break
            
            with contextlib.suppress(discord.HTTPException):
                await ctx.channel.delete_messages((message, response))

            if response.content.lower() == "more":
                continue

            await ctx.send(
                file=discord.File(StringIO("\n".join(messages)), filename="output.txt")
            )

            break

    @staticmethod
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

        return path.relative_to(MEDIA_PATH)

    @staticmethod
    def fetch_model(model):
        return globals().get(model)

    @staticmethod
    def models(names=False, key=None):
        model_list = {
            "ballsdex": [
                "Ball",
                "Regime",
                "Economy",
                "Special",
            ],
            "carfigures": [
                "Car",
                "CarType",
                "Country",
                "Event",
                "FontsPack",
                "Exclusive",
            ],
        }

        return_list = model_list[DIR]

        if not names:
            return_list = [globals().get(x) for x in return_list if globals().get(x) is not None]

        if key is not None:
            return_list = [key(x) for x in return_list]

        return return_list

    @staticmethod
    async def create_model(model, identifier, fields_only=False):
        """
        Creates a model instance while providing default values for all.

        Parameters
        ----------
        model: Model
            The tortoise model you want to use.
        identifier: str
            The name of the model instance.
        fields_only: bool
            Whether you want to return the fields created only or not (debugging).
        """
        fields = {}

        special_list = {
            "Identifiers": ["country", "catch_names", "name"],
            "Ignore": ["id", "short_name"]
        }

        if DIR == "carfigures":
            special_list = {
                "Identifiers": ["fullName", "catchNames", "name"],
                "Ignore": ["id", "shortName"]
            }

        for field, field_type in model._meta.fields_map.items():
            if field_type.null or field in special_list["Ignore"]:
                continue

            if field in special_list["Identifiers"]:
                fields[field] = str(identifier)
                continue

            match field_type.__class__.__name__:
                case "ForeignKeyFieldInstance":
                    if field == "cartype":
                        field = "car_type"

                    casing_field = Utils.casing(field, True)
                    
                    instance = await Utils.fetch_model(casing_field).first()

                    if instance is None:
                        raise Exception(f"Could not find default {casing_field}")

                    fields[field] = instance.pk

                case "BigIntField":
                    fields[field] = 100**8

                case "BackwardFKRelation" | "JSONField":
                    continue

                case _:
                    fields[field] = 1
    
        if fields_only:
            return fields

        await model.create(**fields)

    @staticmethod
    async def get_model(model, identifier):
        """
        Returns a model instance, providing autocorrection.

        Parameters
        ----------
        model: Value
            The model you want to use.
        identifier: str
            The identifier of the model instance you are trying to return.
        """
        correction_list = await model.value.all().values_list(model.extra_data[0], flat=True)

        try:
            returned_model = await model.value.filter(
                **{model.extra_data[0]: Utils.autocorrect(str(identifier), correction_list)}
            )
        except AttributeError:
            raise Exception(f"'{model}' is not a valid model.")

        return returned_model[0]
    
    @staticmethod
    def fetch_fields(model, field_filter=None):
        fetched_list = []

        for field, field_type in model._meta.fields_map.items():
            if field_filter is not None and not field_filter(field, field_type):
                continue
            
            fetched_list.append(field)

        return fetched_list

    @staticmethod
    def get_field(model, field):
        """
        Returns a field from a model.

        Parameters
        ----------
        model: Model
            The tortoise model you want to use.
        field: str
            The field you want to fetch.
        """
        return model._meta.fields_map.get(field)

    @staticmethod
    def autocorrect(string, correction_list, error="does not exist."):
        autocorrection = get_close_matches(string, correction_list)

        if not autocorrection or autocorrection[0] != string:
            suggestion = f"\nDid you mean '{autocorrection[0]}'?" if autocorrection else ""

            raise Exception(f"'{string}' {error}{suggestion}")

        return autocorrection[0]

    @staticmethod
    def extract_str_attr(object):
        expression = r"return\s+self\.(\w+)" # TODO: Add `return str()`

        return re.search(expression, inspect.getsource(object.__str__)).group(1)

    @staticmethod
    def remove_code_markdown(content) -> str:
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        return content.strip("` \n")


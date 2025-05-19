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
from typing import Any, Callable

import discord
from ballsdex.core.models import Ball, BallInstance, Economy, Regime, Special  # noqa: F401, I001
from dateutil.parser import parse as parse_date

START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")
STR_RE = re.compile(r"return\s+self\.(\w+)") # TODO: Add `return str()`

STATIC = os.path.isdir("static")
MEDIA_PATH = "./static/uploads" if STATIC else "./admin_panel/media"

MODELS = [
    "Ball",
    "BallInstance",
    "Regime",
    "Economy",
    "Special",
]


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
    def image_path(path: str) -> bool:
        """
        Formats an image path correctly.

        Parameters
        ----------
        path: str
            The path you want to format.
        """
        full_path = path.replace("/static/uploads/", "")

        if STATIC and full_path[0] == ".":
            full_path = full_path[1:]

        return f"{MEDIA_PATH}/{full_path}"

    @staticmethod
    def is_image(path: str) -> bool:
        """
        Determines if a file is an image if it is found within the correct image directory.

        Parameters
        ----------
        path: str
            The path of the file.
        """
        return os.path.isfile(Utils.image_path(path))

    @staticmethod
    def is_date(string: str) -> bool:
        """
        Determines if a string can be parsed into a date.

        Parameters
        ----------
        string: str
            The string you want to check.
        """
        try:
            parse_date(string)
            return True
        except Exception:
            return False

    @staticmethod
    def pascal_case(string: str) -> str:
        """
        Converts a string from whatever case it's in to PascalCase.

        Parameters
        ----------
        string: str
            The string you want to convert.
        """
        string = string.lower()
        return re.sub(
            r"(_[a-z])", lambda m: m.group(1)[1].upper(), string[:1].upper() + string[1:]
        )

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
            valid_choice = message.content.lower() in ("more", "file")

            return (
                message.author == ctx.message.author and
                message.channel == ctx.channel and valid_choice
            )

        for message in messages:
            if page_length >= 750:
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

            await ctx.send(file=discord.File(StringIO("\n".join(messages)), filename="output.txt"))

            break

    @staticmethod
    async def save_file(attachment: discord.Attachment) -> Path:
        """
        Saves a `discord.Attachment` object into a directory.

        Parameters
        ----------
        attachment: discord.Attachment
            The attachment you want to save.
        """
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
    def fetch_model(model: str):
        """
        Fetches a model's class based on the model name provided.

        Parameters
        ----------
        model: str
            The name of the model you want to fetch.
        """
        return globals().get(Utils.pascal_case(model))

    @staticmethod
    def models(names=False, key: Callable | None = None):
        """
        Returns a list of models.

        Parameters
        ----------
        names: bool
            Whether or not a list of the model's names should be returned instead.
        key: Callable | None
            The model instance of name will be passed through this callable per model.
        """
        model_list = MODELS

        if not names:
            model_list = [
                Utils.fetch_model(x) for x in model_list if Utils.fetch_model(x) is not None
            ]

        if key is not None:
            model_list = [key(x) for x in model_list]

        return model_list

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
            "Ignore": ["id", "short_name"],
        }

        model_ids = Utils.models(True, lambda s: f"{str.lower(s)}_id")

        for field, field_type in model._meta.fields_map.items():
            if field_type.null or field in special_list["Ignore"] or field in model_ids:
                continue

            if field in special_list["Identifiers"]:
                fields[field] = str(identifier)
                continue

            match field_type.__class__.__name__:
                case "ForeignKeyFieldInstance":
                    casing_field = Utils.pascal_case(field)

                    instance = await Utils.fetch_model(casing_field).first()

                    if instance is None:
                        raise Exception(f"Could not find default {casing_field}")

                    fields[f"{field}_id"] = instance.pk

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
    async def get_model(model, identifier: str):
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
    def fetch_fields(model, field_filter: Callable | None = None) -> list[str]:
        """
        Returns a list of a model's fields.

        Parameters
        ----------
        model: Model
            The model you want to fetch fields from.
        field_filter: Callable | None
            If this callable returns False, that specific field won't be included.
        """
        fetched_list = []

        for field, field_type in model._meta.fields_map.items():
            if field_filter is not None and not field_filter(field, field_type):
                continue

            fetched_list.append(field)

        return fetched_list

    @staticmethod
    def get_field(model, field: str):
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
    def autocorrect(string: str, correction_list: list[str], error="does not exist."):
        """
        Autocorrects a string based on the specified `correction_list` 
        and raises an error if there are no strings similiar to the string provided.

        Parameters
        ----------
        string: str
            The base string that will be used for autocorrection.
        correction_list: list[str]
            A list of strings that will be referenced when autocorrecting.
        error: str
            The error message that will be raised when there are no similarities.
        """
        autocorrection = get_close_matches(string, correction_list)

        if not autocorrection or autocorrection[0] != string:
            suggestion = f"\nDid you mean '{autocorrection[0]}'?" if autocorrection else ""

            raise Exception(f"'{string}' {error}{suggestion}")

        return autocorrection[0]

    @staticmethod
    def extract_str_attr(object: Any) -> str:
        """
        Extracts the attribute used in the `__str__` method of a class.

        Parameters
        ----------
        object: Any
            The class you want to fetch the `__str__` attribute from.
        """
        extracted = STR_RE.search(inspect.getsource(object.__str__)).group(1)

        if extracted == "to_string":
            return "pk"

        return extracted

    @staticmethod
    def remove_code_markdown(content: str) -> str:
        """
        Removes code markdown from a message.

        Parameters
        ----------
        content: str
            The content you want to remove the code markdown from.
        """
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        return content.strip("` \n")

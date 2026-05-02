import asyncio
import contextlib
import inspect
import os
import re
from dataclasses import dataclass
from difflib import get_close_matches
from enum import Enum
from io import StringIO
from typing import Any, Callable

import discord
from dateutil.parser import parse as parse_date
from django.core.exceptions import FieldDoesNotExist

from bd_models.models import Ball, Economy, Regime, Special  # noqa: F401, I001

START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
FILENAME_RE = re.compile(r"^(.+)(\.\S+)$")

MODELS = ["Ball", "Regime", "Economy", "Special"]


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
    reference: str = "BD-3.0"


config = Settings()


@dataclass
class Utils:
    """
    Utility functions for DexScript.
    """

    @staticmethod
    def image_path(path: str) -> str:
        """
        Formats an image path correctly.

        Parameters
        ----------
        path: str
            The path you want to format.
        """
        return f"media/{path}"  # What even is the point of this, I should just remove this but I'm too lazy rn so...

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
        return re.sub(r"(_[a-z])", lambda m: m.group(1)[1].upper(), string[:1].upper() + string[1:])

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

            return message.author == ctx.message.author and message.channel == ctx.channel and valid_choice

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

            message = await ctx.send(f"{text} Type `more` to continue or `file` to send all messages in a file")

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
            model_list = [Utils.fetch_model(x) for x in model_list if Utils.fetch_model(x) is not None]

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
            The Django model you want to use.
        identifier: str
            The name of the model instance.
        fields_only: bool
            Whether you want to return the fields created only or not (debugging).
        """
        fields = {}

        special_list = {"Identifiers": ["country", "catch_names", "name"], "Ignore": ["id", "short_name"]}

        model_ids = Utils.models(True, lambda s: f"{str.lower(s)}_id")

        for field in model._meta.get_fields():
            field_name = field.name
            is_nullable = getattr(field, "null", False)

            if is_nullable or field_name in special_list["Ignore"] or field_name in model_ids:
                continue

            if field_name in special_list["Identifiers"]:
                fields[field_name] = str(identifier)
                continue

            match field.__class__.__name__:
                case "ForeignKey":
                    casing_field = Utils.pascal_case(field_name)

                    related_model = field.related_model
                    instance = await related_model.objects.afirst()

                    if instance is None:
                        raise Exception(f"Could not find default {casing_field}")

                    fields[field.attname] = instance.pk

                case "BigIntegerField":
                    fields[field_name] = 100**8

                case "ImageField":
                    fields[field_name] = "capitalist.png"  # Placeholder image

                case "ManyToOneRel" | "ManyToManyRel" | "ManyToManyField" | "JSONField":
                    continue

                case _:
                    fields[field_name] = 1

        if fields_only:
            return fields

        await model.objects.acreate(**fields)

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
        correction_list = [value async for value in model.value.objects.values_list(model.extra_data[0], flat=True)]

        try:
            returned_model = await model.value.objects.filter(
                **{model.extra_data[0]: Utils.autocorrect(str(identifier), correction_list)}
            ).afirst()
        except AttributeError:
            raise Exception(f"'{model}' is not a valid model.")

        if returned_model is None:
            raise Exception(f"No match found for '{identifier}'.")

        return returned_model

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

        for field in model._meta.get_fields():
            if field_filter is not None and not field_filter(field.name, field):
                continue

            fetched_list.append(field.name)

        return fetched_list

    @staticmethod
    def get_field(model, field: str):
        """
        Returns a field from a model.

        Parameters
        ----------
        model: Model
            The Django model you want to use.
        field: str
            The field you want to fetch.
        """
        try:
            return model._meta.get_field(field)
        except FieldDoesNotExist:
            return None

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
    def extract_str_attr(object: Any):
        """
        Extracts the attribute used in the `__str__` method of a class.

        Parameters
        ----------
        object: Any
            The class you want to fetch the `__str__` attribute from.
        """
        expression = r"return\s+self\.(\w+)"  # TODO: Add `return str()`

        return re.search(expression, inspect.getsource(object.__str__)).group(1)

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

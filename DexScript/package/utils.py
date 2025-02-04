import inspect
import os
import re
from dataclasses import dataclass
from difflib import get_close_matches
from enum import Enum
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
    def autocorrect(string, correction_list, error="does not exist."):
        autocorrection = get_close_matches(string, correction_list)

        if not autocorrection or autocorrection[0] != string:
            suggestion = f"\nDid you mean '{autocorrection[0]}'?" if autocorrection else ""

            raise Exception(f"'{string}' {error}{suggestion}")

        return autocorrection[0]

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

        if MEDIA_PATH == "./admin_panel/media":
            return path.relative_to("./admin_panel/media/")

        return path.relative_to("/static/uploads")

    @staticmethod
    def extract_str_attr(object):
        expression = r"return\s+self\.(\w+)"

        return re.search(expression, inspect.getsource(object.__str__)).group(1)

    @staticmethod
    def remove_code_markdown(content) -> str:
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        return content.strip("` \n")
    
    @staticmethod
    def image_path(path) -> bool:
        return f"{MEDIA_PATH}/{path.replace("/static/uploads/", "")}"

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

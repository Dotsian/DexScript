import inspect
import os
import re
from dataclasses import dataclass
from difflib import get_close_matches
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

MEDIA_PATH = "./admin_panel/media" if os.path.isdir("./admin_panel/media") else "/static/uploads"


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
    def is_image(path) -> bool:
        if path.startswith("/static/uploads/"):
            path.replace("/static/uploads/", "")

        return os.path.isfile(f"{MEDIA_PATH}/{path}")

    @staticmethod
    def is_date(string) -> bool:
        try:
            parse_date(string)
            return True
        except Exception:
            return False

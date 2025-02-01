import inspect
import re
import traceback
from dataclasses import dataclass, field as datafield
from enum import Enum
from typing import Any

from dateutil.parser import parse as parse_date

from . import commands
from .utils import config, Utils, DIR

if DIR == "ballsdex":
    from ballsdex.core.models import Ball, Economy, Regime, Special # noqa: F401, I001
else:
    from carfigures.core.models import Car, CarType, Country, Event, FontsPack # noqa: F401, I001


class Types(Enum):
    DEFAULT = 0
    METHOD = 1
    CLASS = 2
    BOOLEAN = 3
    MODEL = 4
    DATETIME = 5


@dataclass
class Value:
    name: Any
    type: Types = Types.DEFAULT
    extra_data: list = datafield(default_factory=list)

    def __str__(self):
        return str(self.name)


@dataclass
class Models:
    """
    Model functions.
    """

    @staticmethod
    def all(names=False, key=None):
        model_list = {
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

        return_list = model_list[DIR]

        if not names:
            return_list = [globals().get(x) for x in return_list if globals().get(x) is not None]

        if key is not None:
            return_list = [key(x) for x in return_list]

        return return_list


class DexScriptParser:
    """
    This class is used to parse DexScript into Python code.
    """

    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot
        self.attachments = ctx.message.attachments

        self.command_classes = inspect.getmembers(
            commands, lambda o: (
                inspect.isclass(o) and issubclass(o, commands.DexCommand) 
                and not issubclass(o, commands.Global) and o.__name__ != "DexCommand"
            )
        )

        self.global_methods = [x for x in dir(commands.Global) if not x.startswith("__")]

    def create_value(self, line):
        value = Value(line)
        lower = line.lower()

        type_dict = {
            Types.METHOD: lower in self.global_methods,
            Types.CLASS: lower in [x[0].lower() for x in self.command_classes],
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
                model = globals().get(line)

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
        split_code = [x for x in code.split("\n") if x.strip() != ""]

        parsed_code = [
            [self.create_value(s.strip()) for s in re.findall(r"[^>]+", line)]
            for line in split_code if not line.strip().startswith("--")
        ]

        for line2 in parsed_code:
            if line2 == []:
                continue
            
            method = line2[0]

            if method.type not in (Types.METHOD, Types.CLASS):
                return self.error(
                    f"'{method.name}' is not a valid command.",
                    traceback.format_exc()
                )
            
            if method.type == Types.CLASS:
                line2.pop(0)
                method = (getattr(commands, method.name.title()), line2[0])
            else:
                method = (commands.Global, line2[0])

            line2.pop(0)

            class_loaded = commands.Global() if method[0] == commands.Global else method[0]()
            class_loaded.__loaded__()

            method_call = getattr(class_loaded, method[1].name.lower())

            try:
                await method_call(self.ctx, *line2)
            except TypeError:
                return self.error(
                    f"Argument missing when calling '{method[1].name}'.",
                    traceback.format_exc()
                )

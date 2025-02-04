import inspect
import re
import traceback
from dataclasses import dataclass
from dataclasses import field as datafield
from enum import Enum
from typing import Any

from dateutil.parser import parse as parse_date

from . import commands
from .utils import DIR, Utils, config


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


class DexScriptParser:
    """
    This class is used to parse DexScript into Python code.
    """

    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot
        # self.attachments = ctx.message.attachments

        self.command_classes = inspect.getmembers(
            commands,
            lambda o: (
                inspect.isclass(o)
                and issubclass(o, commands.DexCommand)
                and not issubclass(o, commands.Global)
                and o.__name__ != "DexCommand"
            ),
        )

        self.global_methods = [x for x in dir(commands.Global) if not x.startswith("__")]

    def create_value(self, line):
        value = Value(line)
        lower = line.lower()

        type_dict = {
            Types.METHOD: lower in self.global_methods,
            Types.CLASS: lower in [x[0].lower() for x in self.command_classes],
            Types.MODEL: lower in Utils.models(True, key=str.lower),
            Types.DATETIME: Utils.is_date(lower) and lower.count("-") >= 2,
            Types.BOOLEAN: lower in ["true", "false"],
        }

        for key, operation in type_dict.items():
            if operation is False:
                continue

            value.type = key
            break

        match value.type:
            case Types.MODEL:
                model = Utils.fetch_model(line)

                if model is None:
                    examples = "Ball, Regime, Special"

                    if DIR == "carfigures":
                        examples = "Car, CarType, Event"

                    raise Exception(
                        f"'{line}' is not a valid model\n"
                        f"Make sure you check your capitalization (e.g. {examples})"
                    )

                string_key = Utils.extract_str_attr(model)

                value.name = model
                value.extra_data.append(string_key)

            case Types.BOOLEAN:
                value.name = lower == "true"

            case Types.DATETIME:
                value.name = parse_date(value.name)

        return value

    def error(self, message, log):
        return (message, log)[config.debug]

    async def execute(self, code: str, run_commands=True):
        split_code = [x for x in code.split("\n") if x.strip() != ""]

        parsed_code = [
            [self.create_value(s.strip()) for s in re.findall(r"[^>]+", line)]
            for line in split_code
            if not line.strip().startswith("--")
        ]

        if not run_commands:
            return parsed_code

        for line2 in parsed_code:
            if line2 == []:
                continue

            method = line2[0]

            if method.type not in (Types.METHOD, Types.CLASS):
                return self.error(
                    f"'{method.name}' is not a valid command.", traceback.format_exc()
                )

            if method.type == Types.CLASS:
                line2.pop(0)
                method = (getattr(commands, method.name.title()), line2[0])
            else:
                method = (commands.Global, line2[0])

            line2.pop(0)

            class_loaded = commands.Global if method[0] == commands.Global else method[0]
            class_loaded = class_loaded(self.bot)
            class_loaded.__loaded__()

            method_call = getattr(class_loaded, method[1].name.lower())

            try:
                await method_call(self.ctx, *line2)
            except TypeError:
                return self.error(
                    f"Argument missing when calling '{method[1].name}'.", traceback.format_exc()
                )

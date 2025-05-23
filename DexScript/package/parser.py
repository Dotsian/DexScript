import inspect
import re
import traceback
from dataclasses import dataclass
from dataclasses import field as datafield
from typing import Any

from dateutil.parser import parse as parse_date

from . import commands
from .utils import Types, Utils, config

PARSER_RE = re.compile(r"[^>]+")


@dataclass
class Value:
    name: str
    type: Types = Types.STRING
    value: Any = None

    extra_data: list = datafield(default_factory=list)

    def __str__(self):
        return self.name


class DexScriptParser:
    """
    This class is used to parse DexScript into Python code.
    """

    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot

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
        value.value = line
        
        lower = line.lower()
        pascal = Utils.pascal_case(line)

        type_dict = {
            Types.METHOD: lower in self.global_methods,
            Types.CLASS: lower in [x[0].lower() for x in self.command_classes],
            Types.MODEL: pascal in Utils.models(True),
            Types.DATETIME: Utils.is_date(lower) and lower.count("-") >= 2,
            Types.BOOLEAN: lower in ["true", "false"],
            Types.HEX: lower.startswith("#"),
            Types.ARRAY: lower.startswith("[") and lower.endswith("]"),
            Types.DICT: lower.startsiwth("{") and lower.endswith("}")
        }

        for key, operation in type_dict.items():
            if operation is False:
                continue

            value.type = key
            break

        match value.type:
            case Types.MODEL:
                model = Utils.fetch_model(pascal, False)

                if model is None:
                    raise Exception(f"'{pascal}' is not a valid model")

                string_key = Utils.extract_str_attr(model)

                value.name = model.__name__
                value.value = model

                value.extra_data.append(string_key)

            case Types.BOOLEAN:
                value.value = lower == "true"

            case Types.DATETIME:
                value.value = parse_date(line)

            case Types.HEX:
                hex_str = str(int(line[1:], 16))

                value.name = hex_str
                value.value = hex_str

            case Types.ARRAY:
                value.value = [self.create_value(x.strip()) for x in line[1:-1].split("|")]
            
            case Types.DICT:
                value_dict = {}
                new_line = line[1:-1]

                for item in new_line.split("|"):
                    keyitems = item.strip().split(">")

                    value = self.create_value(keyitems[1].strip())
    
                    value_dict[keyitems[0].strip()] = value

                value.value = value_dict

        return value

    def parse_split(self, input_string):
        result = []
        buffer = ""
        
        persist = False

        for character in input_string:
            is_string = character in ['"', "'"]
            
            if character == "{" or is_string:
                persist = True
                buffer += "" if is_string else character
                continue
                
            if character == "}" or is_string and persist:
                persist = False
                buffer += "" if is_string else character
                continue
                
            if character == ">" and not persist:
                if buffer.strip():
                    result.append(buffer.strip())
                
                buffer = ""
                continue
            
            buffer += character

        if buffer.strip():
            result.append(buffer.strip())

        return result

    def error(self, message, log):
        return (message, log)[config.debug]

    async def execute(self, code: str, run_commands=True):
        shared_instance = commands.Shared(self.ctx.message.attachments)

        split_code = [x for x in code.split("\n") if x.strip() != ""]

        for line in split_code:
            if line.strip().startswith("--"):
                continue
            
            parsed_code.append([self.create_value(x.strip()) for x in parse_split(line)])

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
            class_loaded = class_loaded(self.bot, shared_instance)
            class_loaded.__loaded__()

            method_call = getattr(class_loaded, method[1].name.lower())

            try:
                await method_call(self.ctx, *line2)
            except TypeError:
                return self.error(
                    f"Argument missing when calling '{method[1].name}'.", traceback.format_exc()
                )

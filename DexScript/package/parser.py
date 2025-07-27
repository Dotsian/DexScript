import inspect
import traceback
from dataclasses import dataclass
from dataclasses import field as datafield
from typing import Any

from dateutil.parser import parse as parse_date

from . import commands
from .utils import Types, Utils, config


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
                and o.__name__ in config.command_groups
            ),
        )

        self.global_methods = [x for x in dir(commands.Global) if not x.startswith("__")]

        if "Global" not in config.command_groups:
            self.global_methods = []

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
            Types.NONE: lower == "nil"
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

            case Types.NONE:
                value.value = None

        return value

    def error(self, message, log):
        return (message, log)[config.debug]

    async def execute(self, code: str, run_commands=True):
        data = []
        new_data = []
        
        entered_indent = False
        iteration_level = 0
        original_index = -1
        
        split_code = [x for x in code.split("\n") if x.strip() != ""]
        
        for line in split_code:
            line_new = line.strip()
            
            if line_new.startswith("--"):
                continue
            
            if not line_new.startswith("|"):
                data.append([line, {}])
                original_index = -1
                
                if entered_indent:
                    iteration_level += 1
                
                continue
            
            if original_index == -1:
                entered_indent = True
                original_index = iteration_level

            split_pipe = line.split("|")[1].strip()

            if ">" not in split_pipe:
                data[original_index][1][split_pipe] = split_pipe
                continue
            
            split_line = line.split("|")[1].split(">")
            key = split_line[0].strip()
            
            data[original_index][1][key] = split_line[1].strip()
            
        for item in data:
            if item[1] == {}:
                new_data.append(item[0])
                continue
            
            statement = item[0]
            
            for key, value in item[1].items():
                new_statement = f"{statement} > {key}"
                
                if key != value:
                    new_statement += f" > {value}"
                    
                new_data.append(new_statement)
    
        parsed_code = []

        for line in new_data:
            parsed_code.append([self.create_value(x.strip()) for x in line.split(">")])

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
            class_loaded = class_loaded(self.bot, self.ctx.message.attachments)
            class_loaded.__loaded__()

            method_call = getattr(class_loaded, method[1].name.lower())

            try:
                await method_call(self.ctx, *line2)
            except TypeError:
                return self.error(
                    f"Argument missing when calling '{method[1].name}'.", traceback.format_exc()
                )

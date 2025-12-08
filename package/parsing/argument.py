from dataclasses import dataclass, field
from typing import Any

from ..command import get_commands, load_extensions
from ..utils.autocorrect import autocorrect
from ..utils.basic import is_date, pascal
from ..utils.functions import all_models, fetch_model
from .enums import Types


@dataclass
class Argument:
    """
    Argument class that holds a value's determines type and extra data.
    """

    value: Any
    type: Types = Types.STRING
    extra: dict[str, Any] = field(default_factory=dict[str, Any])

    @staticmethod
    def fetch_type(string: str, type_map: dict[Types, list[str]] | None = None) -> Types:
        """
        Determines the argument's type.

        Parameters
        ----------
        string: str
            The string that will determine the type.
        type_map: dict[Types, list[str]] | None
            A dictionary that will use additional types.
        """
        lower = string.lower()

        if type_map is not None:
            for key_type, matching in type_map.items():
                if string not in matching:
                    continue

                return key_type

        if lower in ["true", "false"]:
            return Types.BOOLEAN
        elif lower.startswith("#"):
            return Types.HEX
        elif string == "EMPTY":
            return Types.NONE
        elif pascal(lower) in [x.__name__ for x in load_extensions()]:
            return Types.EXTENSION
        elif pascal(lower) in get_commands(load_extensions()):
            return Types.COMMAND
        elif is_date(lower) and lower.count("-") >= 2:
            return Types.DATETIME
        elif lower.startswith("[") and lower.endswith("]"):
            return Types.ARRAY
        elif pascal(string) in all_models():
            return Types.MODEL

        return Types.STRING

    def is_type(self, type: Types) -> bool:
        """
        Determines if a argument is equal to a type.

        Parameters
        ----------
        type: Types
            The type you want to compare.
        """
        return self.type == type

    @classmethod
    def from_str(
        cls, string: str, type_map: dict[Types, list[str]] | None = None, force: bool = False
    ):
        """
        Create an Argument and determines its type and value.

        Parameters
        ----------
        string: str
            The string you want to determines the type from and use as a value.
        type_map: dict[Types, list[str]] | None
            A dictionary that will use additional types.
        force: bool
            Whether or not the determination of the argument's value should ignore errors.
        """
        argument_type = cls.fetch_type(string, type_map)

        match argument_type:
            case Types.MODEL:
                if force:
                    return cls(value=string, type=argument_type)

                p_line = pascal(string)
                model = fetch_model(p_line)

                if model is None:
                    suffix = ""
                    autocorrection = autocorrect(p_line, all_models(True))

                    if autocorrection is not None:
                        suffix += f"\nDid you mean '{autocorrection}'?"

                    raise Exception(f"'{p_line}' is not a valid model{suffix}")

        return cls(value=string, type=argument_type)

    def __repr__(self) -> str:
        return f"Argument(value='{self.value}', type=Types.{self.type.name}, extra={self.extra})"

from enum import Enum


class Types(Enum):
    """
    Contains all DexScript types.
    """

    STRING = 0
    EXTENSION = 1
    COMMAND = 2
    BOOLEAN = 3
    MODEL = 4
    DATETIME = 5
    HEX = 6
    ARRAY = 7
    NONE = 8

from package.parsing.enums import Types
from package.parsing.parser import Parser, ParseRequest

MODELS = [
    "BALL",
    "REGIME",
    "SPECIAL",
    "BALL-INSTANCE",
    "ECONOMY",
    "PLAYER",
    "GUILD-CONFIG",
    "BLACKLISTED-ID",
    "BLACKLISTED-GUILD",
    "FRIENDSHIP",
    "TRADE",
    "TRADE-OBJECT",
    "BLOCK",
]

COMMANDS = [
    "EDIT > British Empire > ENABLED > False",
    "DELETE > BALL > Canada",
    "EDIT > SPECIAL > Shiny > START_DATE > 2022-09-23",
    "EDIT > BALL-INSTANCE > #123 > HEALTH_BONUS > 20",
    "FILE > WRITE > file.py",
    "EDIT > Ancient Greece\n| HEALTH > 1000\n| ATTACK > 500",
]

TYPES = [
    [Types.COMMAND, 0, 0, Types.BOOLEAN],
    [Types.COMMAND, Types.MODEL, 0],
    [Types.COMMAND, Types.MODEL, 0, 0, Types.DATETIME],
    [Types.COMMAND, Types.MODEL, Types.HEX, 0, 0],
    [Types.EXTENSION, Types.COMMAND, 0],
    [Types.COMMAND, 0],
]


def multi_parse(*lines: str) -> list[ParseRequest]:
    """
    Parses multiple lines.

    Parameters
    ----------
    lines: str
        The lines you want to parse.
    """
    return [Parser.parse(line, {Types.MODEL: MODELS}, True) for line in lines]


def test_parsing():
    """
    Tests all provided statements and makes sure all of them succeed.
    """
    requests = multi_parse(*COMMANDS)

    for request in requests:
        if request.success:
            continue

        print(request.content)
        assert False


def test_types():
    """
    Ensures all DexScript types are parsed correctly.
    """
    requests = multi_parse(*COMMANDS)

    for index, request in enumerate(requests):
        for argument, arg_type in zip(request.content, TYPES[index]):
            assert not isinstance(argument, str)

            if argument.type == Types.STRING and arg_type == 0:
                continue

            assert argument.type == arg_type


def test_chaining():
    """
    Ensures chaining functions correctly.
    """
    request = multi_parse(COMMANDS[5])[0]

    for index, value in enumerate(request.content):
        if index < 2:
            continue

        assert isinstance(value, list)

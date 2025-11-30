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
]

TYPES = [
    [0, 0, 0, Types.BOOLEAN],
    [0, Types.MODEL, 0],
    [0, Types.MODEL, 0, 0, Types.DATETIME],
    [0, Types.MODEL, Types.HEX, 0, 0],
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
            if argument.type == Types.STRING and arg_type == 0:
                continue

            assert argument.type == arg_type

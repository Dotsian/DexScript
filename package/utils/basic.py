import re

import dateutil.parser as dateparser

CODE_RE = re.compile(r"^((```sql?)(?=\s)|(```))")
PASCAL_RE = re.compile(r"((-|_)[a-z])")


def is_date(string: str) -> bool:
    """
    Determines if a string can be parsed into a date.

    Parameters
    ----------
    string: str
        The string you want to check.

    Returns
    -------
    bool
        Whether the string is a valid date.
    """
    try:
        dateparser.parse(string)
        return True
    except dateparser.ParserError:
        return False


def pascal(string: str) -> str:
    """
    Converts a string to PascalCase.

    Parameters
    ----------
    string: str
        The string you want to convert.

    Returns
    -------
    str
        A PascalCase version of the string.
    """
    string = string.lower()

    return PASCAL_RE.sub(lambda m: m.group(1)[1].upper(), string[:1].upper() + string[1:])


def strip_markdown(content: str) -> str:
    """
    Removes code markdown from a message.

    Parameters
    ----------
    content: str
        The content you want to remove the code markdown from.

    Returns
    -------
    str
        A string with all code blocks removed.
    """
    if content.startswith("```") and content.endswith("```"):
        return CODE_RE.sub("", content)[:-3]

    return content.strip("` \n")

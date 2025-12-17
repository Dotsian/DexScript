from difflib import get_close_matches


def autocorrect(value: str, references: list[str]) -> str | None:
    """
    Autocorrects a string based on the references provided.

    Parameters
    ----------
    value: str
        The initial value that will be autocorrected.
    references: list[str]
        The references that will be compared to the initial string.

    Returns
    -------
    str | None
        The closest match for the value based on the references if found.
    """
    autocorrection = get_close_matches(value, references)

    if not autocorrection or autocorrection[0] != value:
        return None

    return autocorrection[0]

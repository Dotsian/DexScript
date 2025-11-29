import importlib
import inspect
import re
from typing import Any, Callable

IS_DJANGO = importlib.util.find_spec("tortoise") is None

if IS_DJANGO:
    from . import django_functions as functions
else:
    from . import tortoise_functions as functions

STR_RE = re.compile(r"return\s+(?:str\(\s*self\.(\w+)\s*\)|self\.(\w+))")


def all_models(names: bool = False, key: Callable | None = None) -> list:
    """
    Returns a list of models.

    Parameters
    ----------
    names: bool
        Whether or not a list of the model's names should be returned instead.
    key: Callable | None
        The model instance of name will be passed through this callable per model.
    """
    return functions.all_models(names, key)


def fetch_model(model: str):
    """
    Returns a model's class based on its identifier.

    Parameters
    ----------
    model: str
        The model you want to fetch based on its identifier.
    """
    fetched_model = [x for x in functions.all_models() if x.__name__ == model]

    if len(fetched_model) == 0:
        return None

    return fetched_model[0]


def find_model_from_identifier(identifier: str) -> Any:
    """
    Return's a model's class based on if that model has an instance that's
    found based on its identifier.

    Parameters
    ----------
    identifier: str
        The identifier of the instance.
    """
    return functions.find_model_from_identifier(identifier)


def fetch_str(object: Any) -> str | None:
    """
    Extracts the attribute used in the `__str__` method of a class.

    Parameters
    ----------
    object: Any
        The class you want to fetch the `__str__` attribute from.
    """
    str_match = STR_RE.search(inspect.getsource(object.__str__))

    if str_match is None:
        return None

    return str_match.group(1)

from typing import Callable, cast

from tortoise import Tortoise

from ..errors import ModelNotDeclaredError


def all_models(names: bool = False, key: Callable | None = None) -> list:
    models = Tortoise.apps.get("models")

    if models is None:
        return []

    iterator = models.keys() if names else models.values()

    if key is None:
        return cast(list, iterator)

    return [key(item) for item in iterator]


async def find_model_from_identifier(identifier: str):
    fetched_models = []

    for model in all_models():
        if not await model.exists(identifier):
            continue

        fetched_models.append(model)

    if len(fetched_models) != 1:
        raise ModelNotDeclaredError(identifier, [x.__name__ for x in fetched_models])

    return fetched_models[0]

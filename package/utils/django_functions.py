from typing import Callable, cast

from django.apps import apps

from ..errors import ModelNotDeclaredError


def all_models(names: bool = False, key: Callable | None = None) -> list:
    models = apps.get_app_config("bd_models").get_models()
    iterator = [x.__name__ for x in models] if names else [x for x in models]

    if key is None:
        return cast(list, iterator)

    return [key(item) for item in iterator]


async def find_model_from_identifier(identifier: str):
    fetched_models = []

    for model in all_models():
        if not await model.objects.aexists(identifier):
            continue

        fetched_models.append(model)

    if len(fetched_models) != 1:
        raise ModelNotDeclaredError(identifier, [x.__name__ for x in fetched_models])

    return fetched_models[0]

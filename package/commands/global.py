from typing import Any

from ..command import Command, Extension


class Edit(Command):
    """
    View documentation.
    """

    async def default(self, identifier: str, attribute: str, value: Any):
        print(identifier, attribute, value)

    async def attr(self):
        raise NotImplementedError

    async def multi(self, identifier: str, attributes: list[str], values: list[str]):
        raise NotImplementedError

    async def filter(self):
        raise NotImplementedError


class Update(Command):
    """
    View documentation.
    """

    deprecated = True

    async def default(self, model: str, identifier: str, attribute: str, value: Any):
        await self.redirect("Edit", [model, identifier, attribute, value])


class Delete(Command):
    """
    View documentation.
    """

    async def default(self, identifier: str):
        print(identifier)


class Global(Extension):
    """
    Holds global commands for DexScript.
    """

    prefix = False
    commands = [Edit, Update, Delete]

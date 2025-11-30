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

    async def multi(self):
        raise NotImplementedError

    async def filter(self):
        raise NotImplementedError


class Global(Extension):
    """
    Holds global commands for DexScript.
    """

    prefix = False
    commands = [Edit]

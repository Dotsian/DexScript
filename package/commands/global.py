from typing import Any

from ..command import Command, Extension


class Edit(Command):
    """
    View documentation.
    """

    async def default(self, identifier: str, attribute: str, value: Any):
        print(identifier, attribute, value)
        print(self.pre_args)

    async def attr(attribute: str):
        pass

    async def multi():
        pass

    async def filter():
        pass


class Global(Extension):
    """
    Holds global commands for DexScript.
    """

    prefix = False
    commands = [Edit]

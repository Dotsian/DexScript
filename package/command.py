import importlib
import inspect
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, final

from discord.ext import commands
from packaging.specifiers import SpecifierSet
from packaging.version import parse as parse_version

if os.path.isdir("ballsdex"):
    from ballsdex import __version__ as ballsdex_version

if TYPE_CHECKING:
    from ballsdex import __version__ as ballsdex_version
    from ballsdex.core.bot import BallsDexBot


@dataclass
class Command:
    """
    Base command class for DexScript extensions.
    """

    def __init__(
        self,
        bot: "BallsDexBot",
        ctx: commands.Context["BallsDexBot"],
        bd_version: str | None = None,
    ):
        self.bot = bot
        self.ctx = ctx
        self.attachments = ctx.message.attachments

        self.bd_version = bd_version

        self._log: list[str] = []

    @property
    def attachment(self):
        self.attachments.pop(0)
        return self.attachments[0]

    @property
    def can_load(self) -> bool:
        if self.bd_version is not None:
            bd_version = parse_version(ballsdex_version)
            specifier = SpecifierSet(self.bd_version)

            return bd_version in specifier

        return True

    @final
    def output_log(self, content: str):
        self._log.append(content)

    async def default(self, *args, **kwargs) -> None:
        raise NotImplementedError


@dataclass
class Extension:
    """
    Holds commands.
    """

    prefix: bool = True
    commands: list[type[Command]] = field(default_factory=list[type[Command]])
    dev: bool = False

    def can_load(self, bot: "BallsDexBot") -> bool:
        if self.dev and not bot.dev:
            return False

        return True


def load_extensions(path: str = "package/commands", bot: "BallsDexBot | None" = None):
    """
    Loads all DexScript extensions and returns their class.

    Parameters
    ----------
    path: str
        The directory you want to load from.
    bot: BallsDexBot | None
        Used for ensuring an extension can be loaded.
    """
    imports = [
        importlib.import_module(f"{path.replace('/', '.')}.{x.split('.')[0]}")
        for x in os.listdir(path)
    ]

    members = [
        inspect.getmembers(
            x,
            lambda o: (
                inspect.isclass(o) and issubclass(o, Extension) and o.__name__ != "Extension"
            ),
        )
        for x in imports
    ]

    extensions = []

    for extension in members:
        if len(extension) == 0:
            continue

        if bot is not None and not extension[0][1].can_load(bot):
            continue

        extensions.append(extension[0][1])

    return extensions

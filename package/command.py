import importlib
import inspect
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, final

import discord
from packaging.specifiers import SpecifierSet
from packaging.version import parse as parse_version

if os.path.isdir("ballsdex"):
    from ballsdex import __version__ as ballsdex_version

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


@dataclass
class Command:
    bot: "BallsDexBot"
    ctx: discord.Context["BallsDexBot"]

    bd_version: str | None = None

    _log: list[str] = field(default_factory=list[str])

    @property
    def can_load(self) -> bool:
        bd_version = parse_version(ballsdex_version)
        specifier = SpecifierSet(self.bd_version)

        return all([bd_version in specifier])

    @final
    def output_log(self, content: str):
        self._log.append(content)

    def default(self):
        raise NotImplementedError


@dataclass
class Extension:
    """
    Holds commands.
    """

    prefix: bool = True
    commands: list[Command] = field(default_factory=list[Command])
    dev: bool = False


def load_extensions(path: str = "package/commands"):
    """
    Loads all DexScript extensions and returns their class.

    Parameters
    ----------
    path: str
        The directory you want to load from.
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

        extensions.append(extension[0][1])

    return extensions

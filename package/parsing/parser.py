from dataclasses import dataclass
from typing import TYPE_CHECKING

from discord.ext import commands

from .argument import Argument
from .enums import Types

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


@dataclass
class ParseRequest:
    """
    Hold's the parsed content and whether it succeeded or not.
    """

    content: list[Argument] | str
    success: bool = True

    def __str__(self) -> str:
        return f"ParseRequest => {[str(x) for x in self.content]} ({self.success})"


@dataclass
class Parser:
    """
    Parses DexScript code and holds context required for DexScript commands to run.
    """

    bot: "BallsDexBot"
    ctx: commands.Context["BallsDexBot"]

    @staticmethod
    def _parse(
        code: str, type_map: dict[Types, list[str]] | None = None, force: bool = False
    ) -> list[Argument]:
        """
        Parses DexScript code.

        Parameters
        ----------
        code: str
            The code you want to parse.
        type_map: dict[Types, list[str]] | None
            A dictionary that will use additional types.
        force: bool
            Whether or not the determination of an argument's value should ignore errors.
        """
        parsed: list[Argument] = []
        lines: list[str] = [line for line in code.split("\n") if line.strip() != ""]

        for line in lines:
            s_line: str = line.strip()

            if s_line.startswith("--"):
                continue

            arguments = [x.strip() for x in s_line.split(">")]

            if s_line.startswith("|"):
                chained: list[Argument] = []

                for argument in arguments:
                    if argument.startswith("|"):
                        argument = argument[1:].lstrip()

                    chained.append(Argument.from_str(argument, type_map, force))

                parsed.append(chained)
                continue

            for argument in arguments:
                parsed.append(Argument.from_str(argument, type_map, force))

        return parsed

    @staticmethod
    def parse(
        code: str, type_map: dict[Types, list[str]] | None = None, force: bool = False
    ) -> ParseRequest:
        """
        Parses DexScript code and returns a request, which determines if it failed.

        Parameters
        ----------
        code: str
            The code you want to parse.
        type_map: dict[Types, list[str]] | None
            A dictionary that will use additional types.
        force: bool
            Whether or not the determination of an argument's value should ignore errors.
        """
        success = True
        content: list[Argument] | str = ""

        try:
            content = Parser._parse(code, type_map, force)
        except Exception as error:
            content = str(error)
            success = False

        return ParseRequest(content, success)

    async def call(self, parsed: ParseRequest):
        """
        Executes parsed DexScript code.

        Parameters
        ----------
        parsed: ParseRequest
            The code you want to execute.
        """
        raise NotImplementedError

# # # # # # # # # # # # # # # # # # # # # # # # # # # #
#           OFFICIAL DEXSCRIPT INSTALLER              #
#                                                     #
#     This will install DexScript onto your bot.      #
#   For additional information, read the wiki guide.  #
#  An explanation of the code will be provided below. #
#                                                     #
#      THIS CODE IS RAN VIA THE `EVAL` COMMAND.       #


import os
import re
from base64 import b64decode
from dataclasses import dataclass
from dataclasses import field as datafield
from datetime import datetime
from enum import Enum
from io import StringIO
from traceback import format_exc

import discord
import requests
from discord.ext import commands

DIR = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if DIR == "ballsdex":
    from ballsdex.settings import settings
else:
    from carfigures.settings import settings

UPDATING = os.path.isdir(f"{DIR}/packages/dexscript")


class MigrationType(Enum):
    APPEND = 1
    REPLACE = 2


@dataclass
class InstallerConfig:
    """
    Configuration class for the installer.
    """

    github = ["Dotsian/DexScript", "dev"]
    files = ["__init__.py", "cog.py", "commands.py", "parser.py", "utils.py"]
    appearance = {
        "logo": "https://raw.githubusercontent.com/Dotsian/DexScript/refs/heads/dev/assets/DexScriptLogo.png",
        "logo_error": "https://raw.githubusercontent.com/Dotsian/DexScript/refs/heads/dev/assets/DexScriptLogoError.png",
        "banner": "https://raw.githubusercontent.com/Dotsian/DexScript/refs/heads/dev/assets/DexScriptPromo.png"
    }
    migrations = [
        (
            "||await self.add_cog(Core(self))",
            '||await self.load_extension("$DIR.packages.dexscript")\n',
            MigrationType.APPEND
        ),
        (
            '||await self.load_extension("$DIR.core.dexscript")',
            '||await self.load_extension("$DIR.packages.dexscript")',
            MigrationType.REPLACE
        )
    ]
    path = f"{DIR}/packages/dexscript"

@dataclass
class Logger:
    name: str
    output: list = datafield(default_factory=list)

    def log(self, content, level):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.output.append(f"{current_time} [{self.name}] {level} - {content}")

    def file(self, name: str):
        return discord.File(StringIO("\n".join(self.output)), filename=name)


config = InstallerConfig()
logger = Logger("DEXSCRIPT-INSTALLER")


class InstallerEmbed(discord.Embed):
    def __init__(self, installer, embed_type="setup"):
        super().__init__()

        self.installer = installer

        match embed_type:
            case "setup":
                self.setup()
            case "error":
                self.error()
            case "installed":
                self.installed()

    def setup(self):
        self.title = "DexScript Installation"
        self.description = "Welcome to the DexScript installer!"
        self.color = discord.Color.from_str("#FFF" if DIR == "carfigures" else "#03BAFC")
        self.timestamp = datetime.now()

        latest_version = self.installer.latest_version
        current_version = self.installer.current_version

        if UPDATING and latest_version and current_version and latest_version != current_version:
            self.description += (
                "\n\n**Your current DexScript package version is outdated.**\n"
                f"The latest version of DexScript is version {latest_version}, "
                f"while this DexScript instance is on version {current_version}."
            )

        self.set_image(url=config.appearance["banner"])

    def error(self):
        self.title = "DexScript ERROR"
        self.description = (
            "An error occured within DexScript's installation setup.\n"
            "Please submit a bug report and attach the file provided."
        )
        self.color = discord.Color.red()
        self.timestamp = datetime.now()

        if logger.log != []:
            self.description += f"\n```{logger.log[-1]}```"

        self.installer.interface.attachments.append(logger.file("DexScript.log"))
        
        self.set_image(url=config.appearance["logo_error"])

    def installed(self):
        self.title = "DexScript Installed!"
        self.description = (
            "DexScript has been succesfully installed to your bot.\n"
            f"Run the `{settings.prefix}about` command to view details about DexScript."
        )
        self.color = discord.Color.from_str("#FFF" if DIR == "carfigures" else "#03BAFC")
        self.timestamp = datetime.now()

        self.set_image(url=config.appearance["logo"])


class InstallerView(discord.ui.View):
    def __init__(self, installer):
        super().__init__()
        self.installer = installer

    @discord.ui.button(
        style=discord.ButtonStyle.primary, label="Update" if UPDATING else "Install"
    )
    async def install_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.quit_button.disabled = True

        await interaction.message.edit(**self.installer.interface.fields)

        try:
            await self.installer.install()
        except Exception:
            logger.log(format_exc(), "ERROR")

            self.install_button.disabled = True
            self.uninstall_button.disabled = True
            self.quit_button.disabled = True

            self.installer.interface.embed = InstallerEmbed(self.installer, "error")
        else:
            self.installer.interface.embed = InstallerEmbed(self.installer, "installed")

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    @discord.ui.button(
        style=discord.ButtonStyle.primary, label="Uninstall", disabled=not UPDATING
    )
    async def uninstall_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        # TODO: Add uninstallation
        
        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.red, label="Exit")
    async def quit_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.install_button.disabled = True
        self.quit_button.disabled = True

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()


class InstallerGUI:
    def __init__(self, installer):
        self.loaded = False

        self.installer = installer

        self.embed = InstallerEmbed(installer)
        self.view = InstallerView(installer)

        self.attachments = []

    @property
    def fields(self):
        fields = {"embed": self.embed, "view": self.view}

        if self.attachments != []:
            fields["attachments"] = self.attachments

        return fields

    async def reload(self):
        if not self.loaded:
            self.loaded = True

            await ctx.send(**self.fields)  # type: ignore
            return

        await ctx.message.edit(**self.fields)  # type: ignore


class Installer:
    def __init__(self):
        self.interface = InstallerGUI(self)

    async def install(self):
        if os.path.isfile(f"{DIR}/core/dexscript.py"):
            os.remove(f"{DIR}/core/dexscript.py")

        link = f"https://api.github.com/repos/{config.github[0]}/contents/"

        os.makedirs(config.path, exist_ok=True)

        for file in config.files:
            logger.log(f"Fetching {file} from '{link}/DexScript/package'", "INFO")

            request = requests.get(f"{link}/DexScript/package/{file}", {"ref": config.github[1]})

            if request.status_code != requests.codes.ok:
                raise Exception(
                    f"Request to return {file} from '{link}/DexScript/package' "
                    f"resulted with error code {request.status_code}"
                )

            request = request.json()
            content = b64decode(request["content"])

            with open(f"{config.path}/{file}", "w") as opened_file:
                opened_file.write(content.decode("UTF-8"))

            logger.log(f"Installed {file} from '{link}/DexScript/package'", "INFO")

        logger.log("Applying bot.py migrations", "INFO")

        with open(f"{DIR}/core/bot.py", "r") as read_file:
            lines = read_file.readlines()

        stripped_lines = [x.rstrip() for x in lines]

        for index, line in enumerate(lines):
            for migration in config.migrations:
                original = self.format_migration(migration[0])
                new = self.format_migration(migration[1])

                match migration[2]:
                    case MigrationType.REPLACE:
                        if line.rstrip() != original:
                            continue

                        lines[index] = new
                        break
                    case MigrationType.APPEND:
                        if line.rstrip() != original or lines[index + 1] == new:
                            continue

                        lines.insert(stripped_lines.index(original) + 1, new)

        with open(f"{DIR}/core/bot.py", "w") as write_file:
            write_file.writelines(lines)

        logger.log("Loading DexScript extension", "INFO")

        try:
            await bot.load_extension(config.path.replace("/", "."))  # type: ignore
        except commands.ExtensionAlreadyLoaded:
            await bot.reload_extension(config.path.replace("/", "."))  # type: ignore

        logger.log("DexScript installation finished", "INFO")

    @staticmethod
    def format_migration(line):
        return (
            line.replace("    ", "").replace("|", "    ").replace("/n", "\n").replace("$DIR", DIR)
        )

    @property
    def latest_version(self):
        pyproject_request = requests.get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/pyproject.toml",
            {"ref": config.github[1]},
        )

        if pyproject_request.status_code != requests.codes.ok:
            return

        toml_content = b64decode(pyproject_request.json()["content"]).decode("UTF-8")
        new_version = re.search(r'version\s*=\s*"(.*?)"', toml_content)

        if not new_version:
            return

        return new_version.group(1)

    @property
    def current_version(self):
        if not os.path.isfile(f"{config.path}/cog.py"):
            return

        with open(f"{config.path}/cog.py", "r") as file:
            old_version = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', file.read())

        if not old_version:
            return

        return old_version.group(1)


installer = Installer()
await installer.interface.reload()  # type: ignore

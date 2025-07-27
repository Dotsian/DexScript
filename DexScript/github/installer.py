# # # # # # # # # # # # # # # # # # # # # # # # # # # #
#           OFFICIAL DEXSCRIPT INSTALLER              #
#                                                     #
#     This will install DexScript onto your bot.      #
#   For additional information, read the wiki guide.  #
#  An explanation of the code will be provided below. #
#                                                     #
#      THIS CODE IS RAN VIA THE `EVAL` COMMAND.       #
# # # # # # # # # # # # # # # # # # # # # # # # # # # #


import os
import re
import shutil
from base64 import b64decode
from dataclasses import dataclass
from dataclasses import field as datafield
from datetime import datetime
from io import StringIO
from traceback import format_exc

import discord
import requests
from ballsdex.settings import settings
from discord.ext import commands

UPDATING = os.path.isdir("ballsdex/packages/dexscript")
ASSET_PATH = "https://raw.githubusercontent.com/Dotsian/DexScript/refs/heads/main/assets"


@dataclass
class InstallerConfig:
    """
    Configuration class for the installer.
    """

    github = ["Dotsian/DexScript", "dev"]
    files = ["__init__.py", "cog.py", "commands.py", "parser.py", "utils.py", "config.toml"]
    appearance = {
        "logo": f"{ASSET_PATH}/DexScriptLogo.png",
        "logo_error": f"{ASSET_PATH}/DexScriptLogoError.png",
        "banner": f"{ASSET_PATH}/DexScriptPromo.png",
    }
    uninstall_migrations = [
        '||await self.load_extension("ballsdex.core.dexscript")\n',
        '||await self.load_extension("ballsdex.packages.dexscript")\n',
    ]
    path = "ballsdex/packages/dexscript"


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

        if not hasattr(self, embed_type):
            return

        getattr(self, embed_type)()

    def setup(self):
        self.title = "DexScript Installation"
        self.description = "Welcome to the DexScript installer!"
        self.color = discord.Color.from_str("#03BAFC")
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

        if logger.output != []:
            output = logger.output[-1]

            if len(output) >= 750:
                output = logger.output[-1][:750] + "..."

            self.description += f"\n```{output}```"

        self.installer.interface.attachments = [logger.file("DexScript.log")]

        self.set_thumbnail(url=config.appearance["logo_error"])

    def installed(self):
        self.title = "DexScript Installed!"
        self.description = (
            "DexScript has been succesfully installed to your bot.\n"
            f"Run the `{settings.prefix}about` command to view details about DexScript."
        )
        self.color = discord.Color.from_str("#03BAFC")
        self.timestamp = datetime.now()

        self.set_thumbnail(url=config.appearance["logo"])

    def uninstalled(self):
        self.title = "DexScript Uninstalled!"
        self.description = "DexScript has been succesfully uninstalled from your bot."
        self.color = discord.Color.from_str("#03BAFC")
        self.timestamp = datetime.now()

        self.set_thumbnail(url=config.appearance["logo"])

    def config(self):
        with open(f"{config.path}/config.toml") as file:
            file_contents = file.read()

        self.title = "DexScript Configuration"
        self.description = f"```toml\n{file_contents}\n```"
        self.color = discord.Color.from_str("#03BAFC")
        self.timestamp = datetime.now()


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

            self.installer.interface.embed = InstallerEmbed(self.installer, "error")
        else:
            self.installer.interface.embed = InstallerEmbed(self.installer, "installed")

        self.installer.interface.view = None

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.primary, label="Uninstall", disabled=not UPDATING)
    async def uninstall_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.installer.uninstall()

        self.installer.interface.embed = InstallerEmbed(self.installer, "uninstalled")
        self.installer.interface.view = None

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        label="Config",
        disabled=not os.path.isfile(f"{config.path}/config.toml")
    )
    async def config_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.installer.interface.embed = InstallerEmbed(self.installer, "config")
        self.installer.interface.view = ConfigView(self.installer)

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.red, label="Exit")
    async def quit_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()


class ConfigModal(discord.ui.Modal):
    def __init__(self, installer, setting: str):
        self.installer = installer
        self.setting = setting

        super().__init__(title=f"Editing `{setting}`")

    value = discord.ui.TextInput(label="New value", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        with open(f"{config.path}/config.toml") as file:
            lines = [x.strip() for x in file.readlines()]
            new_lines = []

            for line in lines:
                if not line.startswith(self.setting):
                    new_lines.append(line + "\n")
                    continue

                full_value = self.value.value
                new_value = f'"{full_value}"'

                if full_value.lower() in ["true", "false"]:
                    new_value = full_value.lower()
                elif full_value.startswith("[") and full_value.endswith("]"):
                    new_value = full_value

                new_lines.append(f"{self.setting} = {new_value}\n")

            with open(f"{config.path}/config.toml", "w") as write_file:
                write_file.writelines(new_lines)

        self.installer.interface.embed = InstallerEmbed(self.installer, "config")

        await interaction.message.edit(**self.installer.interface.fields)

        await interaction.response.send_message(
            f"Updated `{self.setting}` to `{self.value.value}`!",
            ephemeral=True
        )


class ConfigSelect(discord.ui.Select):
    def __init__(self, installer):
        self.installer = installer

        options = []

        with open(f"{config.path}/config.toml") as file:
            description = ""

            for line in file.readlines():
                if line.rstrip() in ["\n", "", "]"] or line.startswith(" "):
                    continue

                if line.startswith("#"):
                    description = line[2:]
                    continue

                name = line.split(" ")[0]

                options.append(
                    discord.SelectOption(label=name, value=name, description=description)
                )

                description = ""

        super().__init__(placeholder="Edit setting", max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ConfigModal(self.installer, self.values[0]))


class ConfigView(discord.ui.View):
    def __init__(self, installer):
        super().__init__()
        self.installer = installer

        back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.primary)
        reset_button = discord.ui.Button(label="Reset", style=discord.ButtonStyle.grey)
        quit_button = discord.ui.Button(label="Exit", style=discord.ButtonStyle.red)

        back_button.callback = self.back_button
        reset_button.callback = self.reset_button
        quit_button.callback = self.quit_button

        self.add_item(back_button)
        self.add_item(ConfigSelect(installer))
        self.add_item(reset_button)
        self.add_item(quit_button)

    async def back_button(self, interaction: discord.Interaction):
        self.installer.interface.embed = InstallerEmbed(self.installer, "setup")
        self.installer.interface.view = InstallerView(self.installer)

        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    async def reset_button(self, interaction: discord.Interaction):
        request = requests.get(
            f"https://api.github.com/repos/{config.github[0]}/"
            "contents/DexScript/package/config.toml",
            {"ref": config.github[1]}
        )

        if request.status_code != requests.codes.ok:
            await interaction.response.send_message(
                f"Failed to reset config file `({request.status_code})`", ephemeral=True
            )
            return

        request = request.json()
        content = b64decode(request["content"])

        with open(f"{config.path}/config.toml", "w") as opened_file:
            opened_file.write(content.decode())

        self.installer.interface.embed = InstallerEmbed(self.installer, "config")

        await interaction.message.edit(**self.installer.interface.fields)

        await interaction.response.send_message("Successfully reset config file", ephemeral=True)

    async def quit_button(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True

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

    def has_package_config(self) -> bool:
        with open("config.yml", "r") as file:
            lines = file.readlines()

        return "packages:\n" in lines

    def add_package(self, package: str) -> bool:
        with open("config.yml", "r") as file:
            lines = file.readlines()

        item = f"  - {package}\n"

        if "packages:\n" not in lines:
            return False
        
        if item in lines:
            return True

        for i, line in enumerate(lines):
            if line.rstrip().startswith("packages:"):
                lines.insert(i + 1, item)
                break

        with open("config.yml", "w") as file:
            file.writelines(lines)

        return True

    def uninstall_migrate(self):
        with open("ballsdex/core/bot.py", "r") as read_file:
            lines = read_file.readlines()

        for index, line in enumerate(lines):
            for migration in config.uninstall_migrations:
                original = self.format_migration(migration)

                if line != original:
                    continue

                lines.pop(index)

        with open("ballsdex/core/bot.py", "w") as write_file:
            write_file.writelines(lines)

    async def install(self):
        if not self.has_package_config():
            raise Exception("Your Ballsdex version is no longer compatible with DexScript")

        if os.path.isfile("ballsdex/core/dexscript.py"):
            os.remove("ballsdex/core/dexscript.py")

            await bot.remove_cog("DexScript")  # type: ignore

        link = f"https://api.github.com/repos/{config.github[0]}/contents"

        os.makedirs(config.path, exist_ok=True)

        for file in config.files:
            if file.endswith(".toml") and os.path.isfile(f"{config.path}/{file}"):
                logger.log(f"{file} already exists, skipping", "INFO")
                continue

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
                opened_file.write(content.decode())

            logger.log(f"Installed {file} from '{link}/DexScript/package'", "INFO")

        logger.log("Applying bot.py migrations", "INFO")

        self.add_package(config.path.replace("/", "."))

        logger.log("Loading DexScript extension", "INFO")

        try:
            await bot.reload_extension(config.path.replace("/", "."))  # type: ignore
        except commands.ExtensionNotLoaded:
            await bot.load_extension(config.path.replace("/", "."))  # type: ignore

        logger.log("DexScript installation finished", "INFO")

    async def uninstall(self):
        if os.path.isfile("ballsdex/core/dexscript.py"):
            os.remove("ballsdex/core/dexscript.py")

        shutil.rmtree(config.path)

        self.uninstall_migrate()

        await bot.unload_extension(config.path.replace("/", "."))  # type: ignore

    @staticmethod
    def format_migration(line):
        return line.replace("    ", "").replace("|", "    ").replace("/n", "\n")

    @property
    def latest_version(self):
        pyproject_request = requests.get(
            "https://api.github.com/repos/Dotsian/DexScript/contents/pyproject.toml",
            {"ref": config.github[1]},
        )

        if pyproject_request.status_code != requests.codes.ok:
            return

        toml_content = b64decode(pyproject_request.json()["content"]).decode()
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

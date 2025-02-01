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
import requests
from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime

import discord

DIR = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"
UPDATING = os.path.isdir(f"{DIR}/packages/dexscript")

@dataclass
class InstallerConfig:
    """
    Configuration class for the installer.
    """
    
    github = ["Dotsian/DexScript", "dev"]
    files = ["__init__.py", "cog.py", "commands.py", "parser.py", "utils.py"]
    migrations = [
        (
            "||await self.add_cog(Core(self))",
            '||await self.load_extension("$DIR.packages.dexscript")\n'
        )
    ]
    path = f"{DIR}/packages/dexscript"


config = InstallerConfig()


class InstallerEmbed(discord.Embed):
    def __init__(self, installer):
      super().__init__()

      self.installer = installer

      self.title = "DexScript Installation"
      self.description = "Welcome to the DexScript installer!"
      self.color = discord.Color.from_str("#FFF" if DIR == "carfigures" else "#03BAFC")
      self.timestamp = datetime.now()

      latest_version = self.installer.latest_version
      current_version = self.installer.current_version

      if UPDATING and latest_version is not None and current_version is not None:
        self.description += (
           "\n**Your current DexScript package version is outdated.**\n"
           f"The latest version of DexScript is version {latest_version}, "
           f"while this DexScript instance is on version {current_version}."
        )

      self.set_image(url="https://raw.githubusercontent.com/Dotsian/DexScript/refs/heads/dev/assets/DexScriptPromo.png")


class InstallerView(discord.ui.View):
    def __init__(self, installer):
        super().__init__()
        self.installer = installer

    @discord.ui.button(style=discord.ButtonStyle.primary, label="Update" if UPDATING else "Install")
    async def install_button(self, interaction: discord.Interaction):
        self.install_button.disabled = True
        self.quit_button.disabled = True

        await self.installer.install()
        
        await interaction.message.edit(**self.installer.interface.fields)
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.red, label="Exit")
    async def quit_button(self, interaction: discord.Interaction):
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

  @property
  def fields(self):
    return {"embed": self.embed, "view": self.view}

  async def reload(self):
    if not self.loaded:
      self.loaded = True

      await ctx.send(**main_gui.fields) # type: ignore
      return

    await ctx.message.edit(**main_gui.fields) # type: ignore


class Installer:
    def __init__(self):
       self.interface = InstallerGUI(self)
    
    async def install(self):
        if os.path.isfile(f"{DIR}/core/dexscript.py"):
           os.remove(f"{DIR}/core/dexscript.py")
        
        link = f"https://api.github.com/repos/{config.github[0]}/contents/"

        for file in config.files:
            request = requests.get(f"{link}/DexScript/package/{file}", {"ref": config.github[1]})

            if request.status_code != requests.codes.ok:
                pass # TODO: Add error handling

            request = request.json()
            content = b64decode(request["content"])

            with open(f"{config.path}/{file}", "w") as opened_file:
                opened_file.write(content.decode("UTF-8"))

        with open(f"{DIR}/core/bot.py", "r") as read_file:
            lines = read_file.readlines()

        stripped_lines = [x.rstrip() for x in lines]

        for index, line in enumerate(lines):
            for migration in config.migrations:
                original = self.format_migration(migration[0])
                new = self.format_migration(migration[1])

                if line.rstrip() != original or lines[index + 1] == new:
                    continue

                lines.insert(stripped_lines.index(original) + 1, new)

        with open(f"{DIR}/core/bot.py", "w") as write_file:
            write_file.writelines(lines)

        # try:
            # await bot.load_extension(config.path)
        # except commands.ExtensionAlreadyLoaded:
            # await bot.reload_extension(config.path)

    @staticmethod
    def format_migration(line):
        return (
            line.replace("    ", "")
            .replace("|", "    ")
            .replace("/n", "\n")
            .replace("$DIR", DIR)
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
await installer.interface.reload() # type: ignore

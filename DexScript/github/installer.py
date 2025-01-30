# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#           OFFICIAL DEXSCRIPT INSTALLER              #
#                                                     #
#     This will install DexScript onto your bot.      #
#   For additional information, read the wiki guide.  #
#  An explanation of the code will be provided below. #
#                                                     #
#      THIS CODE IS RAN VIA THE `EVAL` COMMAND.       #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # 


from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from os import path
from time import time
from traceback import format_exc

from requests import codes, get

DIR = "ballsdex" if path.isdir("ballsdex") else "carfigures"

if DIR == "ballsdex":
    from ballsdex.settings import settings
else:
    from carfigures.settings import settings


@dataclass
class InstallerConfig:
    """
    Configuration class for the installer.
    """
    
    github = ["Dotsian/DexScript", "dev"]
    migrations = [
        (
            "¶¶await self.add_cog(Core(self))",
            '¶¶await self.load_extension("$DIR.core.dexscript")\n'
        )
    ]

config = InstallerConfig()

class Installer:
    def __init__(self):
        self.message = None
        self.managed_time = None

        self.keywords = ["Installed", "Installing", "Install"]
        self.updating = path.isfile(f"{DIR}/core/dexscript.py")

        if self.updating:
            self.keywords = ["Updated", "Updating", "Update"]

        self.embed = discord.Embed(
            title=f"{self.keywords[1]} DexScript",
            description=(
                f"DexScript is being {self.keywords[0].lower()} to your bot.\n"
                "Please do not turn off your bot."
            ),
            color=discord.Color.from_str("#03BAFC"),
            timestamp=datetime.now(),
        )

        self.embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")

    @staticmethod
    def format_migration(line):
        return (
            line.replace("    ", "")
            .replace("¶", "    ")
            .replace("/n", "\n")
            .replace("$DIR", DIR)
        )

    async def error(self, error, exception=False):
        self.embed.title = "DexScript ERROR"

        description = (
            f"Please submit a [bug report]"
            f"(<https://github.com/{config.github[0]}/issues/new/choose>) to the GitHub page"
        )

        if exception:
            description += " and attach the file below."
        else:
            description += f".\n```{error}```"

        self.embed.description = description
        self.embed.color = discord.Color.red()

        fields = {"embed": self.embed}

        if exception:
            fields["attachments"] = [discord.File(StringIO(error), filename="DexScript.log")]

        await self.message.edit(**fields)

    async def run(self, ctx):
        """
        Installs or updates the latest DexScript version.

        - Fetches the contents of the `dexscript.py` file from the official DexScript repository, 
          and writes that content onto a local `dexscript.py` file.

        - Apply migrations from the `config.migrations` list onto the `bot.py` file to allow 
          DexScript to load on bot startup.

        - Load or reload the DexScript extension.
        """
        self.message = await ctx.send(embed=self.embed)
        self.managed_time = time()

        link = f"https://api.github.com/repos/{config.github[0]}/contents/"

        request = get(f"{link}/dexscript.py", {"ref": config.github[1]})

        if request.status_code != codes.ok:
            await self.error(
                "Failed to fetch the `dexscript.py` file. "
                f"Recieved request status code `{request.status_code}`."
            )
            return

        request = request.json()
        content = b64decode(request["content"])

        with open(f"{DIR}/core/dexscript.py", "w") as opened_file:
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

        try:
            await bot.load_extension(f"{DIR}.core.dexscript")
        except commands.ExtensionAlreadyLoaded:
            await bot.reload_extension(f"{DIR}.core.dexscript")

        if self.updating:
            request = get(f"{link}/version.txt", {"ref": config.github[1]})

            new_version = (
                b64decode(request.json()["content"]).decode("UTF-8").rstrip()
            )

            self.embed.description = (
                f"DexScript has been updated to v{new_version}.\n"
                f"Use `{settings.prefix}about` to view details about DexScript."
            )
        else:
            self.embed.description = (
                "DexScript has been installed to your bot\n"
                f"Use `{settings.prefix}about` to view details about DexScript."
            )

        self.embed.set_footer(
            text=f"DexScript took {round((time() - self.managed_time) * 1000)}ms "
            f"to {self.keywords[2].lower()}"
        )

        await self.message.edit(embed=self.embed)

installer = Installer()

try:
    await installer.run(ctx)
except Exception:
    installer.embed.set_footer(
        text=f"Error occurred {round((time() - installer.managed_time) * 1000)}ms "
        f"into {installer.keywords[1].lower()}"
    )

    await installer.error(format_exc(), True)

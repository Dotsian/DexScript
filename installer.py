# OFFICIAL DEXSCRIPT INSTALLER
# > This will install DexScript onto your bot.
# > For additional information, read  the wiki guide.
# > An explanation of the code will be provided below.
# THE CODE BELOW IS RAN VIA THE INVOCATION OF THE `EVAL` COMMAND.


from base64 import b64decode
from datetime import datetime
from os import path
from time import time
from traceback import format_exc

from requests import codes, get

dir_type = "ballsdex" if path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
    from ballsdex.settings import settings
else:
    from carfigures.settings import settings

GITHUB = ["Dotsian/DexScript", "main"]

MIGRATIONS = """
Upgrade:
    /-/-await self.add_cog(Core(self)) || /-/-await self.load_extension("$DIR.core.dexscript") -n

Drop:
    from ballsdex.core.dexscript import DexScript -n
"""


class Installer:
    def __init__(self):
        self.message = None
        self.managed_time = None

        self.keywords = ["Installed", "Installing", "Install"]
        self.updating = path.isfile(f"{dir_type}/core/dexscript.py")

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
            .replace("/-", "    ")
            .replace(" -n", "\n")
            .replace("$DIR", dir_type)
        )

    async def error(self, error, log=None):
        final_log = "" if log is None else f"\n\n```\n{log}\n```"

        self.embed.title = "DexScript ERROR"

        self.embed.description = (
            f"{error}\n Please submit a [bug report]"
            f"(<https://github.com/{GITHUB[0]}/issues/new/choose>) to the GitHub page." 
            f"{final_log}"
        )

        self.embed.color = discord.Color.red()

        await self.message.edit(embed=self.embed)

    async def run(self, ctx):
        self.message = await ctx.send(embed=self.embed)

        self.managed_time = time()

        link = f"https://api.github.com/repos/{GITHUB[0]}/contents/"

        # Fetches the `dexscript.py` file for later use.
        request = get(f"{link}/dexscript.py", {"ref": GITHUB[1]})

        if request.status_code != codes.ok:
            await self.error("Failed to fetch the `dexscript.py` file.")
            return

        request = request.json()
        content = b64decode(request["content"])

        migration_dict = {"Upgrade": {}, "Drop": []}
        current_migration = ""

        # Parse the `MIGRATIONS` variable, insert each value into `migration_dict`.
        for line in MIGRATIONS.split("\n"):
            if line == "":
                current_migration = ""

            if current_migration == "Drop":
                migration_dict[current_migration].append(self.format_migration(line))

            if current_migration != "" and "||" in line:
                items = self.format_migration(line).split(" || ")
                migration_dict[current_migration][items[0]] = items[1]

            if line[:-1] in ["Upgrade", "Drop"]:
                current_migration = line[:-1]

        # Create the DexScript file.
        with open(f"{dir_type}/core/dexscript.py", "w") as opened_file:
            opened_file.write(content.decode("UTF-8"))

        # Add the ability to load the DexScript package to the bot.py file.
        # Also applies the migration values from `migration_dict`.
        with open(f"{dir_type}/core/bot.py", "r") as opened_file_1:
            lines = opened_file_1.readlines()
            contents = ""

            for index, line in enumerate(lines):
                if line in migration_dict["Drop"]:
                    continue

                contents += line + "\n"

                for key, item in migration_dict["Upgrade"].items():
                    if line.rstrip() != key or lines[index + 1] == item:
                        continue

                    contents += item

            with open(f"{dir_type}/core/bot.py", "w") as opened_file_2:
                opened_file_2.write(contents)

        # Loads or reloads the DexScript extension.
        try:
            await bot.load_extension(f"{dir_type}.core.dexscript")
        except commands.ExtensionAlreadyLoaded:
            await bot.reload_extension(f"{dir_type}.core.dexscript")

        self.embed.title = f"{self.keywords[0]} DexScript"

        if self.updating:
            request = get(f"{link}/version.txt", {"ref": GITHUB[1]})

            new_version = b64decode(
                request.json()["content"]
            ).decode("UTF-8").rstrip()

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

    await installer.error(
        f"Failed to {installer.keywords[2].lower()} DexScript.", format_exc()
    )

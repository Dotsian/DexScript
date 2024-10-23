from datetime import datetime
from os import path, mkdir
from time import time

from base64 import b64decode
from requests import get, codes
from yaml import dump

dir_type = "ballsdex" if path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
    from ballsdex.settings import settings
else:
    from carfigures.settings import settings


updating = path.isfile(f"{dir_type}/core/dexscript.py")

keywords = [["Updated", "Updating"], ["Installed", "Installing"]][not updating]

embed = discord.Embed(
    title=f"{keywords[1]} DexScript",
    description=(
        f"DexScript is being {keywords[0].lower()} on your bot.\n"
        "Please do not turn off your bot."
    ),
    color=discord.Color.from_str("#03BAFC"),
    timestamp=datetime.now(),
)

embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")

original_message = await ctx.send(embed=embed)

t1 = time()

GITHUB = ["https://api.github.com/repos/Dotsian/DexScript/contents/", {"ref": "beta"}]
BUGLINK = "<https://github.com/Dotsian/DexScript/issues/new/choose>"
request = get(f"{GITHUB[0]}/dexscript.py", GITHUB[1])


async def display_error(error, log=None):
    final_log = f"\n\n```\n{log}\n```" if log is not None else ""

    embed.title = "DexScript ERROR"
    embed.description = (
        f"{error}\n" f"Please submit a [bug report]({BUGLINK}) on the GitHub page." f"{final_log}"
    )
    embed.color = discord.Color.red()

    await original_message.edit(embed=embed)


if request.status_code != codes.ok:
    await display_error("Failed to fetch the `dexscript.py` file.")
    return

request = request.json()
content = b64decode(request["content"])

default_settings = {
    "debug": False,
    "safe_mode": True,
    "outdated_warnings": True,
    "branch": "main"
}

migrations = """
Upgrade:
    import types || import os -n
    /-/-await self.add_cog(Core(self)) || /-/-await self.load_extension("$DIR.core.dexscript") -n
    
Drop:
    from ballsdex.core.dexscript import DexScript -n
"""

migration_dict = {"Upgrade": {}, "Drop": []}
current_migration = ""

def format_migration(line):
    return (
        line.replace("    ", "")
        .replace("/-", "    ")
        .replace(" -n", "\n")
        .replace("$DIR", dir_type)
    )

for line in migrations.split("\n"):
    if line == "":
        current_migration = ""
        
    if current_migration == "Drop":
        migration_dict[current_migration].append(
            format_migration(line)
        )
        
    if current_migration != "" and "||" in line:
        items = format_migration(line).split(" || ")
        migration_dict[current_migration][items[0]] = items[1]
        
    if line[:-1] in ["Upgrade", "Drop"]:
        current_migration = line[:-1]
        print(current_migration)

async def install():
    # Create the data folder for package installation.
    try:
        mkdir(f"{dir_type}/data")
    except FileExistsError:
        pass

    # Create the setting file if it doesn't exist.
    if not path.isfile("script-config.yml"):
        with open("script-config.yml", "w") as opened_file:
            opened_file.write(yaml.dump(default_settings))

    # Create the DexScript file.
    with open(f"{dir_type}/core/dexscript.py", "w") as opened_file:
        opened_file.write(content.decode("UTF-8"))

    # Add the ability to load the DexScript cog to the bot.py file.
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

    # Adds the new package loading system
    with open(f"{dir_type}/core/bot.py", "r") as file:
        code = file.read()

    tracking = False

    for line in code.split("\n"):
        if tracking:
            code = code.replace("\n" + line, "")

        if line == "]" and tracking:
            tracking = False
            break

        if not line.startswith("PACKAGES"):
            continue

        if len(line) == 12:
            tracking = True

        new_line = (
            f'PACKAGES = [x for x in os.listdir("{dir_type}/packages") if x != "__pycache__"]'
        ) 

        code = code.replace(line, new_line.strip())

    with open(f"{dir_type}/core/bot.py", "w") as file:
        file.write(code)

    try:
        await bot.load_extension(f"{dir_type}.core.dexscript")
    except commands.ExtensionAlreadyLoaded:
        await bot.reload_extension(f"{dir_type}.core.dexscript")


keyword = "update" if updating else "install"

try:
    await install()
except Exception as e:
    embed.set_footer(
        text=f"Error occurred {round((time() - t1) * 1000)}ms into {keywords[0].lower()}"
    )

    await display_error(f"Failed to {keyword} DexScript.", e)
    return

t2 = time()

embed.title = f"{keywords[0]} DexScript"

if updating:
    r = get(f"{GITHUB[0]}/version.txt", GITHUB[1])

    new_version = b64decode(r.json()["content"]).decode("UTF-8").rstrip()

    embed.description = (
        f"DexScript has been updated to v{new_version}.\n"
        f"Use `{settings.prefix}about` to view details about DexScript."
    )
else:
    embed.description = (
        "DexScript has been installed to your bot\n"
        f"Use `{settings.prefix}about` to view details about DexScript."
    )  

embed.set_footer(text=f"DexScript took {round((t2 - t1) * 1000)}ms to {keyword}")

await original_message.edit(embed=embed)

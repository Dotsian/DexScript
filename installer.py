import base64
import requests
import datetime
import time
import os


dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
  from ballsdex.settings import settings
else:
  from carfigures.settings import settings


updating = os.path.isfile(f"{dir_type}/core/dexscript.py")

keywords = [x[0 if updating else 1] for x in [["Updating", "Installing"], ["Updated", "Installed"]]]

embed = discord.Embed(
  title = f"{keywords[0]} DexScript",
  description = f"DexScript is being {keywords[1].lower()} on your bot.\nPlease do not turn off your bot.",
  color = discord.Color.from_str("#03BAFC"),
  timestamp = datetime.datetime.now()
)

embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")

original_message = await ctx.send(embed=embed)

t1 = time.time()


GITHUB = "https://api.github.com/repos/Dotsian/DexScript/contents/dexscript.py"
request = requests.get(GITHUB)

if request.status_code != requests.codes.ok:
  await ctx.send("Failed to fetch the DexScript.py file\nReport this issue to dot_zz on Discord.")
  return

request = request.json()
content = base64.b64decode(request["content"])

additions = {
  "        await self.add_cog(Core(self))": (
    f'        await self.load_extension("{dir_type}.core.dexscript")\n'
  ),
}

deprecated = {
  f"from {dir_type}.core.dexscript import DexScript\n": (
    ""
  ),
  "        await self.add_cog(DexScript(self))": (
    f't\tawait self.load_extension("{dir_type}.core.dexscript")'
  )
}

def format_line(line):
  if line in deprecated.keys():
    return deprecated[line]
  
  return line

# Create the DexScript file.
with open(f"{dir_type}/core/dexscript.py", "w") as opened_file:
  opened_file.write(content.decode("UTF-8"))

# Add the ability to load the DexScript cog to the bot.py file.
with open(f"{dir_type}/core/bot.py", "r") as opened_file_1:
  lines = opened_file_1.readlines()
  contents = ""

  for index, line in enumerate(lines):
    contents += line

    for key, item in additions.items():
      if line.rstrip() != key or lines[index + 1] == item:
        continue

      contents += format_line(item)

  with open(f"{dir_type}/core/bot.py", "w") as opened_file_2:
    opened_file_2.write(contents)


try:
  await bot.load_extension(f"{dir_type}.core.dexscript")
except commands.ExtensionAlreadyLoaded:
  await bot.reload_extension(f"{dir_type}.core.dexscript")

t2 = time.time()

embed.title = f"DexScript {keywords[1]}"

if updating:
  r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/version.txt")
  
  new_version = base64.b64decode(r.json()["content"]).decode("UTF-8").rstrip()

  embed.description = (
    f"DexScript has been updated to v{new_version}.\n"
    f"Use `{settings.prefix}about` to view details about DexScript."
  )
else:
  embed.description = (
    "DexScript has been installed to your bot\n"
    f"Use `{settings.prefix}about` to view details about DexScript."
  )

embed.set_footer(
  text = f"DexScript took {round((t2 - t1) * 1000)}ms to {'update' if updating else 'install'}"
)

await original_message.edit(embed=embed)

import base64
import requests
import os

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
  from ballsdex.settings import settings
else:
  from carfigures.settings import settings

await ctx.send("Installing DexScript...")

GITHUB = "https://api.github.com/repos/Dotsian/DexScript/contents/dexscript.py"
request = requests.get(GITHUB)

if request.status_code != requests.codes.ok:
  await ctx.send("Failed to fetch the DexScript.py file\nReport this issue to dot_zz on Discord.")
  return

request = request.json()
content = base64.b64decode(request["content"])

additions = {
  f"from {dir_type}.core.commands import Core": (
    f"from {dir_type}.core.dexscript import DexScript\n"
  ),
  "        await self.add_cog(Core(self))": (
    "        await self.add_cog(DexScript(self))\n"
  ),
}

# Create the DexScript file.
with open(f"{dir_type}/core/dexscript.py", "w") as opened_file:
  contents = content.decode("UTF-8")
  opened_file.write(contents)

# Add the ability to load the DexScript cog to the bot.py file.
with open(f"{dir_type}/core/bot.py", "r") as opened_file_1:
  lines = opened_file_1.readlines()
  contents = ""

  for index, line in enumerate(lines):
    contents += line

    for key, item in additions.items():
      if line.rstrip() != key or lines[index + 1] == item:
        continue

      contents += item

  with open(f"{dir_type}/core/bot.py", "w") as opened_file_2:
    opened_file_2.write(contents)

await ctx.send(f"DexScript has been installed.\nRestart your bot for DexScript to work.\nUse `{settings.prefix}about` to test it out!")

import os

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

await ctx.send("Uninstalling DexScript...")

if os.path.isfile(f"{dir_type}/core/dexscript.py"):
  os.remove(f"{dir_type}/core/dexscript.py")

exclude = [
  f"from {dir_type}.core.dexscript import DexScript",
  "        await self.add_cog(DexScript(self))"
]

# Add the ability to remove DexScript-related code from the bot.py file.
with open(f"{dir_type}/core/bot.py", "r") as opened_file_1:
  lines = opened_file_1.readlines()
  content = ""

  for index, line in enumerate(lines):
    if line.rstrip() in exclude:
      continue

    content += line

  with open(f"{dir_type}/core/bot.py", "w") as opened_file_2:
    opened_file_2.write(content)

await ctx.send("DexScript has been uninstalled.\nRestart your bot for DexScript to be removed.")

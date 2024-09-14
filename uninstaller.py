import os

await ctx.send("Uninstalling DexScript...")

if os.path.isfile("ballsdex/core/dexscript.py"):
  os.remove("ballsdex/core/dexscript.py")

exclude = [
  "from ballsdex.core.dexscript import DexScript",
  "        await self.add_cog(DexScript(self))"
]

# Add the ability to load the DexScript cog to the bot.py file.
with open("ballsdex/core/bot.py", "r") as opened_file_1:
  lines = opened_file_1.readlines()
  content = ""

  for index, line in enumerate(lines):
    if line.rstrip() in exclude:
      print("I HEARD SKIPPING")
      continue

    content += line

  with open("ballsdex/core/bot.py", "w") as opened_file_2:
    opened_file_2.write(content)

await ctx.send("DexScript has been uninstalled.\nRestart your bot for DexScript to be removed.")

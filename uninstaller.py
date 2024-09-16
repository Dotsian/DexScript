import time
import datetime
import os


dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

t1 = time.time()

embed = discord.Embed(
  title = "Removing DexScript",
  description = "DexScript is being removed from your bot.\nPlease do not turn off your bot.",
  color = discord.Color.red(),
  timestamp = datetime.datetime.now()
)

embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")

original_message = await ctx.send(embed=embed)

if os.path.isfile(f"{dir_type}/core/dexscript.py"):
  os.remove(f"{dir_type}/core/dexscript.py")

exclude = [
  f"from {dir_type}.core.dexscript import DexScript",
  "        await self.add_cog(DexScript(self))",
  f'        await self.load_extension("{dir_type}.core.dexscript")'
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

await bot.remove_cog("DexScript")

t2 = time.time()

embed.title = "DexScript Removed"
embed.description = (
  "DexScript has been removed from your bot.\n"
  "All DexScript-related commands have been removed."
)
embed.set_footer(
  text = f"DexScript took {round((t2 - t1) * 1000)}ms to uninstall"
)

await original_message.edit(embed=embed)
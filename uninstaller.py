import os

await ctx.send("Uninstalling DexScript...")

os.remove("ballsdex/core/dexscript.py")

# Add the ability to load the DexScript cog to the bot.py file.
with open("ballsdex/core/bot.py", "r") as opened_file_1:
  read = opened_file_1.read()

  read.replace("from ballsdex.core.dexscript import DexScript\n", "")
  read.replace("        await self.add_cog(DexScript(self))\n", "")

  with open("ballsdex/core/bot.py", "w") as opened_file_2:
    opened_file_2.write(read)

await ctx.send("DexScript has been uninstalled.\nRestart your bot for DexScript to be removed.")

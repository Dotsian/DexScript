import datetime
import os
import time

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

t1 = time.time()

embed = discord.Embed(
    title="Removing DexScript",
    description="DexScript is being removed from your bot.\nPlease do not turn off your bot.",
    color=discord.Color.red(),
    timestamp=datetime.datetime.now(),
)

embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")

original_message = await ctx.send(embed=embed)


async def uninstall():
    if os.path.isfile("script-config.yml"):
        os.remove("script-config.yml")
    
    if os.path.isfile(f"{dir_type}/core/dexscript.py"):
        os.remove(f"{dir_type}/core/dexscript.py")

    exclude = [
        f"from {dir_type}.core.dexscript import DexScript",
        "        await self.add_cog(DexScript(self))",
        f'        await self.load_extension("{dir_type}.core.dexscript")',
    ]

    # Add the ability to remove DexScript-related code from the bot.py file.
    with open(f"{dir_type}/core/bot.py", "r") as opened_file_1:
        lines = opened_file_1.readlines()
        content = ""

        for line in lines:
            if line.rstrip() in exclude:
                continue

            content += line

        with open(f"{dir_type}/core/bot.py", "w") as opened_file_2:
            opened_file_2.write(content)

    await bot.remove_cog("DexScript")


try:
    await uninstall()
except Exception as e:
    link = "<https://github.com/Dotsian/DexScript/issues/new/choose>"

    embed.title = "DexScript ERROR"
    embed.description = (
        "DexScript failed to uninstall.\n"
        f"Please submit a [bug report]({link}) on the GitHub page.\n\n"
        f"```\nERROR: {e}\n```"
    )

    embed.set_footer(
        text=f"Error occurred {round((time.time() - t1) * 1000)}ms into uninstallation"
    )

    await original_message.edit(embed=embed)
    return

t2 = time.time()

embed.title = "DexScript Removed"
embed.description = (
    "DexScript has been removed from your bot.\n"
    "All DexScript-related commands have been removed."
)
embed.set_footer(text=f"DexScript took {round((t2 - t1) * 1000)}ms to uninstall")

await original_message.edit(embed=embed)

# DexScript - ALPHA

DexScript is a set of commands developed by DotZZ on September 14, 2024, used for BallsDex Discord bot forks.
Below is a guide on how to use DexScript, and what DexScript is capable of.
Currently, DexScript is in alpha. DexScript will have more commands, the ability to support more models, and overall quality-of-life improvements as time passes.

## Installation

Installing DexScript to your Discord bot is easy. All you need is permission to use the `eval` command.
To install and update DexScript for your Discord bot, download `dexscript.py` in this repository, copy the code below, and run it using the `eval` command:

> You must have eval permissions to run this command.

```py
# THIS CODE WILL INSTALL OR UPDATE DEXSCRIPT FOR YOUR DISCORD BOT.


from ballsdex.settings import settings

await ctx.send("Installing DexScript...")

if ctx.message.attachments == []:
  await ctx.send("You must attach the `dexscript.py` file.")
  return

file = ctx.message.attachments[0]

# Create the DexScript file.
with open("ballsdex/core/dexscript.py", "w") as opened_file:
  contents = await file.read()
  opened_file.write(contents.decode("utf-8"))

# Add the ability to load the DexScript cog to the bot.py file.
with open("ballsdex/core/bot.py", "r") as opened_file_1:
  lines = opened_file_1.readlines()
  contents = ""

  for line in lines:
    contents += line
  
    if "from ballsdex.core.commands import Core" in line:
      contents += "from ballsdex.core.dexscript import DexScript\n"
    elif "await self.add_cog(Core(self))" in line:
      contents += "        await self.add_cog(DexScript(self))\n"
  
  with open("ballsdex/core/bot.py", "w") as opened_file_2:
    opened_file_2.write(contents)

await ctx.send(f"DexScript has been installed.\nRestart your bot for DexScript to work.\nUse `{settings.prefix}about` to test it out!")
```

After you run the installation code, you must restart the bot for the commands to take effect.
DexScript should be up and running when you're finished!

## Commands

There are three commands DexScript has at the moment.

1. **UPDATE**
2. **REMOVE**
3. **DISPLAY**

To run a command, you must put `b.run`, swapping `b.` with your bot's prefix.

-----------

### UPDATE

The `UPDATE` command updates a ball depending on the field given. The function is structured like this:<br>
```sql
UPDATE > BALL > ball_name > FIELD > value
```

> You can not update spawn and card art, as of right now.

- `ball_name` has to be replaced with the country of the ball you are trying to edit.
- `FIELD` has to be replaced with the field you are trying to edit. (EXAMPLE: CREDITS)
- `value` has to be replaced with the new value you want that field to be.

Changing a Roman Empire ball's credits (EXAMPLE):<br>
```sql
UPDATE > BALL > Roman Empire > CREDITS > dotzz (Spawn & Card)
```

-----------

### REMOVE

The `REMOVE` command deletes a ball depending on the name given:<br>
```sql
REMOVE > BALL > ball_name
```

- `ball_name` has to be replaced with the country of the ball you are trying to delete.

Deleting a Parthian Empire ball (EXAMPLE):<br>
```sql
REMOVE > BALL > Parthian Empire
```

-----------

### DISPLAY

The `DISPLAY` command displays the value of a specified field for a ball:<br>
```sql
DISPLAY > BALL > ball_name > FIELD
```

- `ball_name` has to be replaced with the country of the ball you are trying to access.
- `FIELD` has to be replaced with the field you are trying to view. (EXAMPLE: ATTACK)

Displaying an Ancient Greece ball's health (EXAMPLE):<br>
```sql
DISPLAY > BALL > Ancient Greece > HEALTH
```

-----------

Written by DotZZ
DexScript Version: 0.1

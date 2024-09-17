# DexScript - ALPHA

DexScript is a set of commands developed by DotZZ on September 14, 2024, used for **BallsDex and CarFigures** Discord bot forks.
Below is a guide on how to use DexScript, and what DexScript is capable of.
Currently, DexScript is in alpha. DexScript will have more commands, the ability to support more models, and overall quality-of-life improvements as time passes.

<img src="https://i.imgur.com/uKfx0qO.png" width="200"> 

## Installation & Updating

> [!NOTE]
> Using the same command to install DexScript will update if DexScript is detected in your Discord bot.

Installing and updating DexScript to your Discord bot is easy. All you need is permission to use the `eval` command.
To install and update DexScript for your Discord bot, copy the code below and run it using the `eval` command:

```py
import base64, requests
r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/installer.py")

if r.status_code == requests.codes.ok:
  content = base64.b64decode(r.json()["content"])
  await ctx.invoke(bot.get_command("eval"), body=content.decode("UTF-8"))
else:
  await ctx.send("Failed to install DexScript.\nReport this issue to `dot_zz` on Discord.")
```

After you run the installation code, you must restart the bot for the commands to take effect.
DexScript should be up and running when you're finished!

## Uninstalling

Uninstalling is the same as installing DexScript. All you need is permission to use the `eval` command.
To uninstall DexScript, copy the code below and run it using the `eval` command:

```py
import base64, requests
r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/uninstaller.py")

if r.status_code == requests.codes.ok:
  content = base64.b64decode(r.json()["content"])
  await ctx.invoke(bot.get_command("eval"), body=content.decode("UTF-8"))
else:
  await ctx.send("Failed to uninstall DexScript.\nReport this issue to `dot_zz` on Discord.")
```

## Commands

There are five commands DexScript has at the moment. <br>
All commands will be explained in the guide below.

1. **CREATE**
2. **UPDATE**
3. **REMOVE**
4. **DISPLAY**
5. **LIST**

To run a command, you must put `b.run`, swapping `b.` with your bot's prefix.

-----------

> [!WARNING]
> CarFigures uses different field names for their models. Some of the examples below might not work on CarFigures. In order to find out what fields are in a model, use the `list` command.

### CREATE

The `CREATE` command creates a model depending on the name given. After creating a model, you must update it via the `UPDATE` command to edit it. The function is structured like this:<br>
```sql
CREATE > MODEL > model_name
```

- `MODEL` has to be replaced with the model you are trying to create. (REGIME, BALL, ECONOMY, etc.)
- `model_name` has to be replaced with the model name you are trying to create.

Creating a Greece ball (BALLSDEX EXAMPLE):<br>
```sql
CREATE > BALL > Greece
```

Creating an economy (BALLSDEX EXAMPLE):<br>
```sql
UPDATE > ECONOMY > Anarchism
```

-----------

### UPDATE

The `UPDATE` command updates a model depending on the field given. The function is structured like this:<br>
```sql
UPDATE > MODEL > model_name > FIELD > value
```

- `MODEL` has to be replaced with the model you are trying to edit. (REGIME, BALL, ECONOMY, etc.)
- `model_name` has to be replaced with the model name you are trying to edit. (EXAMPLE: Ancient Thebes)
- `FIELD` has to be replaced with the field you are trying to edit. (EXAMPLE: CREDITS)
- `value` has to be replaced with the new value you want that field to be.

Changing a Roman Empire ball's credits (BALLSDEX EXAMPLE):<br>
```sql
UPDATE > BALL > Roman Empire > CREDITS > dotzz (Spawn & Card)
```

Changing a regime's name (BALLSDEX EXAMPLE):<br>
```sql
UPDATE > REGIME > Democracy > NAME > NewRegime
```

-----------

### REMOVE

The `REMOVE` command deletes a model depending on the name given:<br>
```sql
REMOVE > MODEL > model_name
```

- `MODEL` has to be replaced with the model you are trying to delete. (REGIME, BALL, ECONOMY, etc.)
- `model_name` has to be replaced with the model name you are trying to delete.

Deleting a Parthian Empire ball (BALLSDEX EXAMPLE):<br>
```sql
REMOVE > BALL > Parthian Empire
```

Deleting an economy (BALLSDEX EXAMPLE):<br>
```sql
REMOVE > ECONOMY > Capitalism
```

-----------

### DISPLAY

The `DISPLAY` command displays the value of a specified field for a model:<br>
```sql
DISPLAY > MODEL > model_name > FIELD
```

- `MODEL` has to be replaced with the model you are trying to access. (REGIME, BALL, ECONOMY, etc.)
- `model_name` has to be replaced with the model name you are trying to access.
- `FIELD` has to be replaced with the field you are trying to view. (EXAMPLE: ATTACK)

Displaying an Ancient Greece ball's health (BALLSDEX EXAMPLE):<br>
```sql
DISPLAY > BALL > Ancient Greece > HEALTH
```

Displaying a regime's name (BALLSDEX EXAMPLE):<br>
```sql
DISPLAY > REGIME > Dictatorship > NAME
```

-----------

### LIST

The `LIST` command displays a list of all a model's fields:<br>
```sql
LIST > MODEL
```

- `MODEL` has to be replaced with the model you are trying to list. (REGIME, BALL, ECONOMY, etc.)

Displaying a list of fields a ball has (BALLSDEX EXAMPLE):<br>
```sql
LIST > BALL
```

Displaying a list of fields an economy has (BALLSDEX EXAMPLE):<br>
```sql
LIST > ECONOMY
```

-----------

Written by DotZZ <br>
DexScript Version: 0.3

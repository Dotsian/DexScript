# DexScript - BETA

![DexScript Banner](assets/DexScriptPromo.png)

[![Ruff](https://github.com/Dotsian/DexScript/actions/workflows/ruff.yml/badge.svg)](https://github.com/Dotsian/DexScript/actions/workflows/ruff.yml)
[![Issues](https://img.shields.io/github/issues/Dotsian/DexScript)](https://github.com/Dotsian/DexScript/issues)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

## What is DexScript?

DexScript is a set of commands for Ballsdex and CarFigures created by DotZZ that expands on the standalone admin commands and substitutes for the admin panel. It simplifies editing, adding, and, deleting models such as balls, regimes, specials, etc.

Let's say you wanted to update a ball's rarity to 2. You could run `UPDATE > BALL > Mongolia > RARITY > 2.0`.

![Updating rarity showcase](assets/screenshots/showcase1.png)

DexScript has a ton more features too! All of them can be found within our extensive documentation. Here's a simple list of the most popular features.

* Creating Models: `CREATE > Ball > Dex Empire` - creates a ball called "Dex Empire"
* Updating Models: `UPDATE > Regime > Democracy > name > Monarchy` - updates the democracy regime's name to "Monarchy"
* Deleting Models: `DELETE > Special > Lunar New Year` - deletes an event called "Lunar New Year"
* Mass Updating Models: `FILTER > UPDATE > Ball > rarity > 5.0 > 10.0 > GT` - Updates all balls with higher than a rarity of 5 to a rarity of 10.
* Mass Deleting Models: `FILTER > DELETE > Special > enabled > False` - Deletes all events that aren't enabled.
* Eval Presets: `EVAL > SAVE > show leaderboard` and `EVAL > RUN > show leaderboard` - saves an eval called "show leaderboard" and runs it.

## Installation

### Requirements

To install DexScript, you must have the following:

* Ballsdex or CarFigures v2.2.0+
* Eval access

### Installing

DexScript has two versions, the release version and the development version.

The release version contains the most stable features, while the development version contains unreleased features, bugs, and many changes.

To install DexScript, run the following eval command:

#### Release Version

```py
import base64, requests; await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/installer.py").json()["content"]).decode())
```

#### Development Version

```py
import base64, requests; await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/DexScript/github/installer.py", {"ref": "dev"}).json()["content"]).decode())

```

## Updating

The command above will automatically update DexScript, however, if you already have DexScript, you can run `b.upgrade` to update DexScript, replacing `b.` with your bot's prefix.

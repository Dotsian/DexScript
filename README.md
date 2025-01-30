<a name="logo"/>
<div align="center">
<img src="https://i.imgur.com/uKfx0qO.png" alt="DexScript logo" width="200" height="200"></img>
</div>

# DexScript - BETA

[![Ruff](https://github.com/Dotsian/DexScript/actions/workflows/ruff.yml/badge.svg)](https://github.com/Dotsian/DexScript/actions/workflows/ruff.yml)
[![Issues](https://img.shields.io/github/issues/Dotsian/DexScript)](https://github.com/Dotsian/DexScript/issues)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

DexScript is a set of commands created by DotZZ. The commands simplify editing, adding, and deleting models such as balls, regimes, specials, etc.

DexScript supports both BallsDex and CarFigures. Each fork has its own respective guide on how to use DexScript with it.

## Installation

### Requirements

To install DexScript, you must have the following:

* Ballsdex or CarFigures v2.2.0+
* Eval access

### Installing

DexScript has two branches: Main and Dev.

The main branch contains the most stable features, while the dev branch contains unreleased features, a plenthora of bugs, and many changes.

To install DexScript, run the following eval command:

#### Main

```py
import base64, requests

await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/installer.py").json()["content"]).decode())
```

### Dev

```py
import base64, requests

await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/DexScript/github/installer.py", {"ref": "dev"}).json()["content"]).decode())
```

## Updating

The command above will automatically update DexScript, however, if you already have DexScript, you can run `DEV > EXEC_GIT > Dotsian/DexScript/installer.py` to update DexScript.

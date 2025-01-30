<a name="logo"/>
<div align="center">
<img src="https://i.imgur.com/uKfx0qO.png" alt="DexScript logo" width="200" height="200"></img>
</div>

# DexScript - BETA

[![Ruff](https://github.com/Dotsian/DexScript/actions/workflows/ruff.yml/badge.svg)](https://github.com/Dotsian/DexScript/actions/workflows/ruff.yml)
[![Issues](https://img.shields.io/github/issues/Dotsian/DexScript)](https://github.com/Dotsian/DexScript/issues)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

DexScript is a set of commands for Ballsdex and CarFigures created by DotZZ that expands on the standalone admin commands and substitutes for the admin panel. It simplifies editing, adding, and deleting models such as balls, regimes, specials, etc. 

## Installation

### Requirements

To install DexScript, you must have the following:

* Ballsdex or CarFigures v2.2.0+
* Eval access

### Installing

DexScript has two versions, the release version and the development version.

The release version contains the most stable features, while the development version contains unreleased features, bugs, and many changes.

To install DexScript, run the following eval command:

<details>
<summary><strong>Release Version</strong></summary>

```py
import base64, requests

await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/installer.py").json()["content"]).decode())
```
</details>

<details>
<summary><strong>Development Version</strong></summary>

```py
import base64, requests

await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/DexScript/github/installer.py", {"ref": "dev"}).json()["content"]).decode())
```
</details>

## Updating

The command above will automatically update DexScript, however, if you already have DexScript, you can run `DEV > EXEC_GIT > Dotsian/DexScript/installer.py` to update DexScript.

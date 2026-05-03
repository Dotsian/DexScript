# DexScript - BETA (BD-3.0)

![DexScript Banner](assets/DexScriptPromo.png)

[![Ruff](https://github.com/Caylies/DexScript/actions/workflows/ruff.yml/badge.svg)](https://github.com/Caylies/DexScript/actions/workflows/ruff.yml)
[![Issues](https://img.shields.io/github/issues/Caylies/DexScript)](https://github.com/Caylies/DexScript/issues)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

## What is DexScript?

DexScript is a DSL package for Ballsdex created by Cayla that allows you to easily perform operations on balls, regimes, specials, etc.

Let's say you wanted to update a ball's rarity to `2.0`. You could run `UPDATE > BALL > Mongolia > RARITY > 2.0`.

![Updating rarity showcase](assets/screenshots/showcase1.png)

## Installation

Add the following into your `config/extra.toml` file.

```toml
[[ballsdex.packages]]
location = "git+https://github.com/Caylies/DexScript.git@v0.5.1#BD-3.0"
path = "dexscript"
enabled = true
```

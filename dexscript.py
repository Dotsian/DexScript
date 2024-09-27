import base64
import os
import time
import logging
import re
import requests
import traceback
from difflib import get_close_matches
from enum import Enum

import discord
from discord.ext import commands

dir_type = "ballsdex" if os.path.isdir("ballsdex") else "carfigures"

if dir_type == "ballsdex":
  from ballsdex.core.models import Ball, Regime
  from ballsdex.packages.admin.cog import save_file
  from ballsdex.settings import settings
else:
  from carfigures.core.models import Car as Ball
  from carfigures.core.models import CarType as Regime
  from carfigures.packages.superuser.cog import save_file
  from carfigures.settings import settings


log = logging.getLogger(f"{dir_type}.core.dexscript")

__version__ = "0.4"


START_CODE_BLOCK_RE = re.compile(r"^((```sql?)(?=\s)|(```))")

MODELS = {
  "ball": Ball,
  "regime": Regime,
}

KEYWORDS = [
  "local",
  "global",
]

dex_globals = {}

outdated_warning = True
advanced_errors = False
  

class Types(Enum):
  METHOD = 0
  NUMBER = 1
  STRING = 2
  BOOLEAN = 3
  VARIABLE = 4
  KEYWORD = 5
  MODEL = 6


class CodeStatus(Enum):
   SUCCESS = 0
   FAILURE = 1
  

class Value():
  def __init__(self, name: str, type: Types, level: int):
    self.name = name
    self.type = type
    self.level = level

  def __repr__(self):
    return self.name
    

class Methods():
  def __init__(
    self, 
    parser, 
    ctx, 
    args: list[Value]
  ):
    self.ctx = ctx
    self.args = args
    
    self.parser = parser

  async def delete(self):
    pass

  async def update(self):
    pass

  async def show(self):
    await self.ctx.send(f"```\n{self.args[1]}\n```")
    
    
class DexScriptParser():
  """
  This class is used to parse DexScript into Python code.
  """

  def __init__(self, ctx):
    self.ctx = ctx
    
    self.dex_locals = {}
    
    self.values = []

  @staticmethod
  def is_number(string):
    try:
      float(string)
      return True
    except ValueError:
      return False

  @staticmethod
  def enclosed(string, border):
    return string[:1] == border and string[-1:] == border

  @staticmethod
  def autocorrect(string, correction_list, error="does not exist."):
    autocorrection = get_close_matches(string, correction_list)

    if not autocorrection or autocorrection[0] != string:
      suggestion = f"\nDid you mean '{autocorrection[0]}'?" if autocorrection else ""

      raise ValueError(f"'{string}' {error}{suggestion}")

    return autocorrection[0]

  def var(self, value):
    return_value = value
    
    match value.type:
      case Types.VARIABLE:
        return_value = value
    
        if value.name in self.dex_locals:
          return_value = self.dex_locals[value.name]
        elif value.name in dex_globals:
          return_value = dex_globals[value.name]
        else:
          raise NameError(f"'{value.name}' is an uknown variable.")

      case Types.BOOLEAN:
        return_value = value.lower() == "true"

    return return_value

  @staticmethod
  def translate(string, item=None):
    """
    CarFigure support.
    """

    if dir_type == "ballsdex":
      return getattr(item, string) if item else string

    translation = {
      "BALL": "ENTITY",
      "COUNTRY": "full_name"
    }

    translated_string = translation.get(string.upper(), string)

    return getattr(item, translated_string) if item else translated_string

  def keyword(self, line):
    identity = line[1].name
    value = line[2].name

    match line[0].name.lower():
      case "local":
          self.dex_locals[identity] = value
      case "global":
          dex_globals[identity] = value

  def create_value(self, line, level):
    type = Types.VARIABLE
    
    value = Value(line, type, level)
    lower = line.lower()
  
    if lower in vars(Methods):
      type = Types.METHOD
    elif lower in KEYWORDS:
      type = Types.KEYWORD
    elif lower in MODELS:
      type = Types.MODEL
    elif self.is_number(lower):
      type = Types.NUMBER
    elif lower in ["true", "false"]:
      type = Types.BOOLEAN
    elif self.enclosed(lower, '"') or self.enclosed(lower, "'"):
      type = Types.STRING

    value.type = type
  
    return self.var(value)
        
  async def execute(self, code: str):
    if (seperator := "\n") not in code:
      seperator = ";"

    split_code = [x for x in code.split(seperator) if x.strip() != ""]

    parsed_code: list[list[Value]] = []
    
    for index, line in enumerate(split_code):
      line_code: list[Value] = []
      full_line = ""
    
      for index2, char in enumerate(line):
        if char == "":
          continue
          
        full_line += char

        if full_line == "--":
          continue
        
        if char in [">"] or index2 == len(line) - 1:
          line_code.append(self.create_value(
            full_line.replace(">", "").strip(), 
            level
          ))
          
          full_line = ""

          if len(line_code) == len(line.split(">")):
            parsed_code.append(line_code)
  
    try:
      for line2 in parsed_code:
        for value in line2:
          if value.type == Types.KEYWORD:
            self.keyword(parsed_code)
            continue

          if value.type != Types.METHOD:
            continue
            
          new_method = Methods(
            self,
            self.ctx,
            line2
          )
          
          await getattr(new_method, value.name.lower())()
    except Exception as error:
      return (error, CodeStatus.FAILURE)
  
    return (None, CodeStatus.SUCCESS)

class DexScript(commands.Cog):
    """
    DexScript commands
    """

    def __init__(self, bot):
      self.bot = bot

    @staticmethod
    def cleanup_code(content): 
      """
      Automatically removes code blocks from the code.
      """

      if content.startswith("```") and content.endswith("```"):
        return START_CODE_BLOCK_RE.sub("", content)[:-3]

      return content.strip("` \n")

    @staticmethod
    def check_version():
      if not outdated_warning:
        return None

      r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/version.txt")

      if r.status_code != requests.codes.ok:
        return

      new_version = base64.b64decode(r.json()["content"]).decode("UTF-8").rstrip()

      if new_version != __version__:
        return (
          f"Your DexScript version ({__version__}) is outdated. " 
          f"Please update to version ({new_version}) "
          f"using `{settings.prefix}update-ds`."
        )

      return None

    @commands.command()
    @commands.is_owner()
    async def run(self, ctx: commands.Context, *, code: str):
      """
      Executes DexScript code.

      Parameters
      ----------
      code: str
        The code you'd like to execute.
      """

      body = self.cleanup_code(code)

      version_check = self.check_version()

      if version_check:
        await ctx.send(f"-# {version_check}")

      dexscript_instance = DexScriptParser(ctx)
      result, status = await dexscript_instance.execute(body)

      if status == CodeStatus.FAILURE:
        full_error = result

        if advanced_errors:
          full_error = traceback.format_exc()
          
        await ctx.send(f"```ERROR: {full_error}\n```")
      else:
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.is_owner()
    async def about(self, ctx: commands.Context):
      """
      Displays information about DexScript.
      """

      embed = discord.Embed(
        title="DexScript - ALPHA",
        description=(
          "DexScript is a set of commands created by DotZZ "
          "that allows you to easily "
          "modify, delete, and display model data.\n\n"
          "For a guide on how to use DexScript, "
          "refer to the official [DexScript guide](<https://github.com/Dotsian/DexScript/wiki/Commands>).\n\n"
          "If you want to follow DexScript, "
          "join the official [DexScript Discord](<https://discord.gg/EhCxuNQfzt>) server."
        ),
        color = discord.Color.from_str("#03BAFC")
      )

      value = ""
      version_check = "OUTDATED" if self.check_version() is not None else "LATEST"

      embed.set_thumbnail(url="https://i.imgur.com/uKfx0qO.png")
      embed.set_footer(text=f"DexScript {__version__} ({version_check})")

      await ctx.send(embed=embed)

    @commands.command(name="update-ds")
    @commands.is_owner()
    async def update_ds(self, ctx: commands.Context):
      """
      Updates DexScript to the latest version.
      """

      r = requests.get("https://api.github.com/repos/Dotsian/DexScript/contents/installer.py")

      if r.status_code == requests.codes.ok:
        content = base64.b64decode(r.json()["content"])
        await ctx.invoke(self.bot.get_command("eval"), body=content.decode("UTF-8"))
      else:
        await ctx.send(
          "Failed to update DexScript.\n"
          "Report this issue to `dot_zz` on Discord."
        )
        print(f"ERROR CODE: {r.status_code}")

    @commands.command(name="reload-ds")
    @commands.is_owner()
    async def reload_ds(self, ctx: commands.Context):
      """
      Reloads DexScript.
      """

      await self.bot.reload_extension(f"{dir_type}.core.dexscript")
      await ctx.send("Reloaded DexScript")

    @commands.command()
    @commands.is_owner()
    async def toggle(self, ctx: commands.Context, setting: str):
      """
      Toggles a setting on and off.

      Parameters
      ----------
      setting: str
        The setting you want to toggle. (DEBUG & OUTDATED-WARNING)
      """

      global advanced_errors
      global outdated_warning

      response = "Setting could not be found."

      match setting:
        case "DEBUG":
          advanced_errors = not advanced_errors
          response = f"Debug mode has been set to `{str(advanced_errors)}`"
        case "OUTDATED-WARNING":
          outdated_warning = not outdated_warning
          response = f"Outdated warnings have been set to `{str(outdated_warning)}`"

      await ctx.send(response)

async def setup(bot):
  await bot.add_cog(DexScript(bot))

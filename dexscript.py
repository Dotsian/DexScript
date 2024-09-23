import os
from difflib import get_close_matches
from enum import Enum

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

MODELS = {
  "ball": Ball,
  "regime": Regime,
}

KEYWORDS = [
  "local",
  "global",
]

dex_globals = {}


def dexmethod(function):
  def wrapper(*args):
    args[0].args.pop(0)
    
    return function(*args)

  return wrapper
  

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
  def __init__(self, name, type):
    self.name = name
    self.type = type

  def __repr__(self):
    return self.name
    

class Methods():
  def __init__(self, parser, ctx, args):
    self.ctx = ctx
    self.args = args
    self.parser = parser

  @dexmethod
  async def create(self):
    fields = {}

    for key, field in vars(self.args[0]()).items():
      if field is not None:
          continue

      if key == "id" or key == "short_name":
          continue

      fields[key] = 1

      if key in [self.parser.translate("country"), "catch_names", "name", "username"]:
          fields[key] = self.args[1]
      elif key == "emoji_id":
          fields[key] = 100 ** 8

    await self.args[0].create(**fields)
    
    await self.ctx.send(
      f"Created `{self.args[1]}` {self.args[0].lower()}\n"
      f"-# Use the `UPDATE` command to update this {self.args[0].lower()}."
    )

  @dexmethod
  def delete(self):
    pass

  @dexmethod
  def update(self):
    pass

  @dexmethod
  def view(self):
    await self.parser.get_model(model, formatted_values[1][0])

    #if formatted_ball[2][0] == "-ALL":
        #pass

    attribute = getattr(returned_model, formatted_values[2][0].lower())

    if isinstance(attribute, str) and os.path.isfile(attribute[1:]):
        await self.ctx.send(
            f"```{attribute}```", file=discord.File(attribute[1:])
        )
        return

    await self.ctx.send(
        f"```{getattr(returned_model, formatted_values[2][0].lower())}```"
    )
    
  @dexmethod
  async def list(self):
    final = f"{str(self.args[0])} FIELDS:\n\n"
    
    for field in vars(self.args[0]()):
      if field.startswith("_"):
        continue

      final += f"- {field}\n"

    await self.ctx.send(f"```{final}```")

  @dexmethod
  async def show(self):
    await self.ctx.send(f"```{self.args[0]}```")
    
    
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

  async def get_model(self, model, identifier):
    return_model = None
    new_identity = await self.autocorrect(identifier, [])

    if dir_type == "ballsdex":
        return_model = await Ball.get(country=new_identity)
    else:
        return_model = await Ball.get(full_name=new_identity)

    return return_model

  def keyword(self, line):
    identity = line[1].name
    value = line[2].name

    match line[0].name.lower():
      case "local":
          self.dex_locals[identity] = value
      case "global":
          dex_globals[identity] = value

  def create_value(self, line):
    type = Types.VARIABLE
    
    value = Value(line, type)
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
        
  def execute(self, code: str):
    if (seperator := "\n") not in code:
      seperator = ";"
    
    for line in code.split(seperator):
      parsed_code = []
    
      full_line = ""
    
      for index, char in enumerate(line):
        if char == "":
          continue
          
        full_line += char

        if full_line == "--":
          continue
        
        if char in [">"] or index == len(line) - 1:
          value_line = full_line.replace(">", "").strip()
          parsed_code.append(self.create_value(value_line))
          full_line = ""
  
      try:
        for value in parsed_code:
          if value.type == Types.METHOD:
            getattr(
              Methods(self, self.ctx, parsed_code), 
              value.name.lower()
            )()
          elif value.type == Types.KEYWORD:
            self.keyword(parsed_code)
      except Exception as error:
        return (error, CodeStatus.FAILURE)
  
    return (None, CodeStatus.SUCCESS)

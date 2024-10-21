from inspect import signature
from typing import Any, Optional


def create(
    model: Any, 
    identifier: str, 
    create_yield: bool = False
):
    model = "Hello"
    suffix = ""

    if model is not None:
        suffix = " and yielded it until `push`"

    print(f"Created `{identifier}`{suffix}")
    
args = signature(create)

arguments = []
    
for arg in args.parameters:
    if str(arg) == "self":
        continue
    
    argument = args.parameters[arg]
    split = str(argument).split(":")
    
    value = [split[0], split[1].strip(), False]
    
    if "=" in split[1]:
        value[2] = True
        value[1] = split[1].split("=")[0].strip()
    
    arguments.append(value)
    
print(arguments)
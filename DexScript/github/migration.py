from os import path

DIR = "ballsdex" if path.isdir("ballsdex") else "carfigures"


#|-----------------------------------------------------------------------------------------|#


def repair_bot_file():
    """
    Repairs the `bot.py` file and removes extra newlines caused by an old DexScript installer.
    """
    with open(f"{DIR}/core/bot.py", "r") as file:
        content = file.read()

        if "import asyncio\n\n" not in content:
            return

    new_lines = []
    last_was_newline = False

    for line in content.splitlines(keepends=True):
        if last_was_newline and line == "\n":
            continue

        last_was_newline = line == "\n"
        new_lines.append(line)

    with open(f"{DIR}/core/bot.py", "w") as file:
        file.writelines(new_lines)


#|-----------------------------------------------------------------------------------------|#


repair_bot_file()

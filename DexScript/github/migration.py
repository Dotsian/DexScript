from os import path


# |-----------------------------------------------------------------------------------------|#


def repair_bot_file():
    """
    Repairs the `bot.py` file and removes extra newlines caused by an old DexScript installer.
    """
    new_lines = []

    with open("ballsdex/core/bot.py", "r") as file:
        if "import asyncio\n\n" not in file.read():
            return

    with open("ballsdex/core/bot.py", "r") as file:
        last_was_newline = False

        for line in file.readlines():
            if last_was_newline is True:
                last_was_newline = False
                continue
            
            if line.endswith("\n") and line != "\n" or line == "\n":
                last_was_newline = True

            new_lines.append(line)

    with open("ballsdex/core/bot.py", "w") as file:
        file.writelines(new_lines)


# |-----------------------------------------------------------------------------------------|#


repair_bot_file()

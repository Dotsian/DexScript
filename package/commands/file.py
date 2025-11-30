import os

from ..command import Command, Extension


class Write(Command):
    """
    View documentation.
    """

    bd_version = "<3.0.0"

    async def default(self, path: str):
        if self.attachments == []:
            if os.path.isfile(path):
                raise Exception(f"{path} already exists.")

            with open(path, "w"):
                pass

            self.output_log(f"Created `{path}`")
            return

        new_file = self.attachment

        await new_file.save(path)

        self.output_log(f"Wrote to `{path}` from `{new_file.filename}`")


class File(Extension):
    """
    File commands.
    """

    commands = [Write]
    dev = True

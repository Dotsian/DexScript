import asyncio
import os
import shutil
from dataclasses import dataclass
from dataclasses import field as datafield

import discord

from .utils import Types, Utils


@dataclass
class Shared:
    """
    Values that will be retained throughout the entire code execution.
    """

    attachments: list = datafield(default_factory=list)


class DexCommand:
    """
    Default class for all dex commands.
    """

    def __init__(self, bot, shared):
        self.bot = bot
        self.shared = shared

    def __loaded__(self):
        pass

    def attribute_error(self, model, attribute):
        if model.value is None or hasattr(model.value(), attribute):
            return
        
        raise Exception(
            f"'{attribute}' is not a valid {model.name} attribute\n"
            f"Run `ATTRIBUTES > {model.name}` to see a list of "
            "all attributes for that model"
        )


class Global(DexCommand):
    """
    Main methods for DexScript.
    """

    async def create(self, ctx, model, identifier):
        """
        Creates a model instance.

        Documentation
        -------------
        CREATE > MODEL > IDENTIFIER
        """
        await Utils.create_model(model.value, identifier)
        await ctx.send(f"Created `{identifier}`")

    async def delete(self, ctx, model, identifier):
        """
        Deletes a model instance.

        Documentation
        -------------
        DELETE > MODEL > IDENTIFIER
        """
        await Utils.get_model(model, identifier).delete()
        await ctx.send(f"Deleted `{identifier}`")

    async def update(self, ctx, model, identifier, attribute, value=None):
        """
        Updates a model instance's attribute. If value is None, it will check
        for any attachments.

        Documentation
        -------------
        UPDATE > MODEL > IDENTIFIER > ATTRIBUTE > VALUE(?)
        """
        attribute_name = attribute.name.lower()
        new_value = None if value is None else value.value

        returned_model = await Utils.get_model(model, identifier)
        self.attribute_error(model, attribute_name)

        model_field = Utils.get_field(model.value, attribute_name)

        image_fields = Utils.fetch_fields(
            model.value,
            lambda _, field_type: (
                field_type.__class__.__name__ == "CharField" and field_type.max_length == 200
            ),
        )

        if value is None and self.shared.attachments and model_field in image_fields:
            image_path = await Utils.save_file(self.shared.attachments.pop(0))
            new_value = Utils.image_path(str(image_path))

        if attribute.type == Types.MODEL:
            attribute_name = f"{attribute.name.lower()}_id"
            attribute_model = await Utils.get_model(attribute, value.name)
            new_value = attribute_model.pk

        setattr(returned_model, attribute_name, new_value)
        await returned_model.save(update_fields=[attribute_name])

        await ctx.send(f"Updated `{identifier}'s` {attribute} to `{value.name}`")

    async def view(self, ctx, model, identifier, attribute=None):
        """
        Displays an attribute of a model instance. If `ATTRIBUTE` is left blank,
        it will display every attribute of that model instance.

        Documentation
        -------------
        VIEW > MODEL > IDENTIFIER > ATTRIBUTE(?)
        """
        returned_model = await Utils.get_model(model, identifier)

        if attribute is None:
            fields = {"content": "```"}

            for key, value in vars(returned_model).items():
                if key.startswith("_"):
                    continue

                fields["content"] += f"{key}: {value}\n"

                if isinstance(value, str) and Utils.is_image(value):
                    fields.setdefault("files", []).append(discord.File(Utils.image_path(value)))

            fields["content"] += "```"
            await ctx.send(**fields)
            return

        attribute_name = attribute.name.lower()
        self.attribute_error(model, attribute_name)

        new_attribute = getattr(returned_model, attribute_name)

        if isinstance(new_attribute, str) and os.path.isfile(new_attribute[1:]):
            await ctx.send(f"```{new_attribute}```", file=discord.File(new_attribute[1:]))
            return

        if attribute.type == Types.MODEL:
            new_attribute = await new_attribute.values_list(attribute.extra_data[0], flat=True)

        await ctx.send(f"```{new_attribute}```")

    async def attributes(self, ctx, model):
        """
        Lists all changeable attributes of a model.

        Documentation
        -------------
        ATTRIBUTES > MODEL
        """
        fields = [
            f"- {x.upper()}"
            for x in Utils.fetch_fields(
                model.value, lambda _, field_type: field_type != "BackwardFKRelation"
            )
        ]

        fields.insert(0, f"{model.name.upper()} ATTRIBUTES:\n")

        await Utils.message_list(ctx, fields)


class Filter(DexCommand):
    """
    Filter commands used for mass updating, deleting, and viewing models.
    """
    
    async def update(self, ctx, model, attribute, old_value, new_value, tortoise_operator=None):
        """
        Updates all instances of a model to the specified value where the specified attribute
        meets the condition  defined by the optional `TORTOISE_OPERATOR` argument
        (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER > UPDATE > MODEL > ATTRIBUTE > OLD_VALUE > NEW_VALUE > TORTOISE_OPERATOR(?)
        """
        casing_name = attribute.name.lower()
        self.attribute_error(model, casing_name)

        if tortoise_operator is not None:
            casing_name += f"__{tortoise_operator.name.lower()}"

        value_old, value_new = old_value.value, new_value.value

        if attribute.type == Types.MODEL:
            value_old = await Utils.get_model(attribute, value_old)
            value_new = await Utils.get_model(attribute, value_new)

        await model.value.filter(**{casing_name: value_old}).update(**{casing_name: value_new})

        await ctx.send(
            f"Updated all `{model.name}` instances from a `{attribute}` "
            f"value of `{old_value}` to `{new_value}`"
        )

    async def delete(self, ctx, model, attribute, value, tortoise_operator=None):
        """
        Deletes all instances of a model where the specified attribute meets the condition
        defined by the optional `TORTOISE_OPERATOR` argument
        (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER > DELETE > MODEL > ATTRIBUTE > VALUE > TORTOISE_OPERATOR(?)
        """
        casing_name = attribute.name.lower()
        self.attribute_error(model, casing_name)

        if tortoise_operator is not None:
            casing_name += f"__{tortoise_operator.name.lower()}"

        new_value = value.value

        if attribute.type == Types.MODEL:
            new_value = await Utils.get_model(attribute, new_value)

        await model.name.filter(**{casing_name: new_value}).delete()

        await ctx.send(
            f"Deleted all `{model.name}` instances with a `{attribute}` "
            f"value of `{value}`"
        )

    async def view(self, ctx, model, attribute, value, tortoise_operator=None):
        """
        Displays all instances of a model where the specified attribute meets the condition
        defined by the optional `TORTOISE_OPERATOR` argument
        (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER > VIEW > MODEL > ATTRIBUTE > VALUE > TORTOISE_OPERATOR(?)
        """
        casing_name = attribute.name.lower()
        self.attribute_error(model, casing_name)

        if tortoise_operator is not None:
            casing_name += f"__{tortoise_operator.name.lower()}"

        new_value = value.value

        if attribute.type == Types.MODEL:
            new_value = await Utils.get_model(attribute, new_value)

        instances = await model.name.filter(**{casing_name: new_value}).values_list(
            model.extra_data[0], flat=True
        )

        await Utils.message_list(ctx, instances)


class Eval(DexCommand):
    """
    Commands for managing eval presets.
    """

    def __loaded__(self):
        os.makedirs("eval_presets", exist_ok=True)

    async def save(self, ctx, name):
        """
        Saves an eval preset.

        Documentation
        -------------
        EVAL > SAVE > NAME
        """
        NAME_LIMIT = 100

        if len(name.name) > NAME_LIMIT:
            raise Exception(
                f"`{name}` exceeds the {NAME_LIMIT}-character limit ({len(name)} > {NAME_LIMIT})"
            )

        if os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` already exists.")

        await ctx.send("Please send the eval command below...")

        try:
            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.message.author,
                timeout=20,
            )
        except asyncio.TimeoutError:
            await ctx.send("Eval preset saving has timed out.")
            return

        with open(f"eval_presets/{name}.py", "w") as file:
            file.write(Utils.remove_code_markdown(message.content))

        await ctx.send(f"`{name}` eval preset has been saved!")

    async def remove(self, ctx, name):
        """
        Removes an eval preset.

        Documentation
        -------------
        EVAL > REMOVE > NAME
        """
        if not os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` does not exists")

        os.remove(f"eval_presets/{name}.py")

        await ctx.send(f"Removed `{name}` preset.")

    async def list(self, ctx):
        if os.listdir("eval_presets") == []:
            await ctx.send("You have no eval presets saved.")
            return

        await Utils.message_list(ctx, os.listdir("eval_presets"))

    async def run(self, ctx, name):  # TODO: Allow args to be passed through `run`.
        """
        Runs an eval preset.

        Documentation
        -------------
        EVAL > RUN > NAME
        """
        if not os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` does not exists")

        with open(f"eval_presets/{name}.py", "r") as file:
            try:
                await ctx.invoke(self.bot.get_command("eval"), body=file.read())
            except Exception as error:
                raise Exception(error)
            else:
                await ctx.message.add_reaction("✅")


class File(DexCommand):
    """
    Commands for managing and modifying the bot's internal filesystem.
    """

    async def read(self, ctx, file_path):
        """
        Sends a file based on the specified file path.

        Documentation
        -------------
        FILE > READ > FILE_PATH
        """
        await ctx.send(file=discord.File(file_path.name))

    async def write(self, ctx, file_path):
        """
        Writes to a file using the attached file's contents.

        Documentation
        -------------
        FILE > WRITE > FILE_PATH
        """
        new_file = ctx.message.attachments[0]

        with open(file_path.name, "w") as opened_file:
            contents = await new_file.read()
            opened_file.write(contents.decode("utf-8"))

        await ctx.send(f"Wrote to `{file_path}`")

    async def clear(self, ctx, file_path):
        """
        Clears the contents of a file.

        Documentation
        -------------
        FILE > CLEAR > FILE_PATH
        """
        if not os.path.isfile(file_path):
            raise Exception(f"'{file_path}' does not exist")

        with open(file_path.name, "w") as _:
            pass

        await ctx.send(f"Cleared `{file_path}`")

    async def listdir(self, ctx, file_path=None):
        """
        Lists all files inside of a directory.

        Documentation
        -------------
        FILE > LISTDIR > FILE_PATH(?)
        """
        path = file_path.name if file_path is not None else None

        await Utils.message_list(ctx, os.listdir(path))

    async def delete(self, ctx, file_path):
        """
        Deletes a file or directory based on the specified file path.

        Documentation
        -------------
        FILE > DELETE > FILE_PATH
        """
        is_dir = os.path.isdir(file_path.name)

        file_type = "directory" if is_dir else "file"

        if is_dir:
            shutil.rmtree(file_path.name)
        else:
            os.remove(file_path.name)

        await ctx.send(f"Deleted `{file_path}` {file_type}")

class Template(DexCommand):
    """
    Template commands used to assist with DexScript commands.
    """

    # TODO: Softcode model creation template.
    async def create(self, ctx, model, argument=None):
        """
        Sends the `create` template for a model.

        Documentation
        -------------
        TEMPLATE > CREATE > BALL > ARGUMENT(?)
        """
        match model.name.lower():
            case "ball":
                template_commands = [
                    f"CREATE > BALL > {argument}",
                    f"UPDATE > BALL > {argument} > REGIME > ...",
                    f"UPDATE > BALL > {argument} > HEALTH > ...",
                    f"UPDATE > BALL > {argument} > ATTACK > ...",
                    f"UPDATE > BALL > {argument} > RARITY > ...",
                    f"UPDATE > BALL > {argument} > EMOJI_ID > ...",
                    f"UPDATE > BALL > {argument} > CREDITS > ...",
                    f"UPDATE > BALL > {argument} > CAPACITY_NAME > ...",
                    f"UPDATE > BALL > {argument} > CAPACITY_DESCRIPTION > ..."
                ]

                await ctx.send(f"```sql\n{'\n'.join(template_commands)}\n```")

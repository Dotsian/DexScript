import asyncio
import os
import shutil

import discord

from .utils import DIR, Types, Utils


class DexCommand:
    def __init__(self, bot):
        self.bot = bot

    def __loaded__(self):
        pass

    def attribute_error(self, model, attribute):
        raise Exception(
            f"'{attribute}' is not a valid {model.name.__name__} attribute\n"
            f"Run `ATTRIBUTES > {model.name.__name__}` to see a list of "
            "all attributes for that model"
        )

    async def create_model(self, model, identifier, fields_only=False):
        fields = {}

        special_list = {
            "Identifiers": ["country", "catch_names", "name"],
            "Ignore": ["id", "short_name"]
        }

        if DIR == "carfigures":
            special_list = {
                "Identifiers": ["fullName", "catchNames", "name"],
                "Ignore": ["id", "shortName"]
            }

        for field, field_type in model._meta.fields_map.items():
            if field_type.null or field in special_list["Ignore"]:
                continue

            if field in special_list["Identifiers"]:
                fields[field] = identifier
                continue

            match field_type.__class__.__name__:
                case "ForeignKeyFieldInstance":
                    if field == "cartype":
                        field = "car_type"

                    casing_field = Utils.casing(field, True)
                    
                    instance = await Utils.fetch_model(casing_field).first()

                    if instance is None:
                        raise Exception(f"Could not find default {casing_field}")

                    fields[field] = instance.pk

                case "BigIntField":
                    fields[field] = 100**8

                case "BackwardFKRelation" | "JSONField":
                    continue

                case _:
                    fields[field] = 1
    
        if fields_only:
            return fields

        await model.create(**fields)

    async def get_model(self, model, identifier):
        correction_list = await model.name.all().values_list(model.extra_data[0], flat=True)

        try:
            returned_model = await model.name.filter(
                **{model.extra_data[0]: Utils.autocorrect(identifier, correction_list)}
            )
        except AttributeError:
            raise Exception(f"'{model}' is not a valid model.")

        return returned_model[0]


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
        await self.create_model(model.name, identifier.name)
        await ctx.send(f"Created `{identifier}`")

    async def delete(self, ctx, model, identifier):
        """
        Deletes a model instance.

        Documentation
        -------------
        DELETE > MODEL > IDENTIFIER
        """
        await self.get_model(model, identifier.name).delete()
        await ctx.send(f"Deleted `{identifier}`")

    async def update(self, ctx, model, identifier, attribute, value=None):
        """
        Updates a model instance's attribute. If value is None, it will check
        for any attachments.

        Documentation
        -------------
        UPDATE > MODEL > IDENTIFIER > ATTRIBUTE > VALUE(?)
        """
        _attr_name = attribute.name.__name__ if attribute.type == Types.MODEL else attribute.name

        attribute_name = Utils.casing(_attr_name.lower())
        new_value = Utils.casing(value.name) if value is not None else None

        returned_model = await self.get_model(model, identifier.name)

        if not hasattr(model.name(), attribute_name):
            self.attribute_error(model, attribute_name)

        if value is None:
            image_path = await Utils.save_file(ctx.message.attachments[0])
            new_value = Utils.image_path(str(image_path))

        text = f"Updated `{identifier}'s` {attribute} to `{new_value}`"

        if attribute.type == Types.MODEL:
            attribute_name = Utils.to_snake_case(_attr_name.lower()) + "_id"

            attribute_model = await self.get_model(attribute, value.name)
            new_value = attribute_model.pk

            text = (
                f"Updated `{identifier}'s` {attribute_model.__class__.__name__} "
                f"to `{value.name}`"
            )

        setattr(returned_model, attribute_name, new_value)

        await returned_model.save(update_fields=[attribute_name])
        await ctx.send(text)

    async def view(self, ctx, model, identifier, attribute=None):
        """
        Displays an attribute of a model instance. If `ATTRIBUTE` is left blank,
        it will display every attribute of that model instance.

        Documentation
        -------------
        VIEW > MODEL > IDENTIFIER > ATTRIBUTE(?)
        """
        returned_model = await self.get_model(model, identifier.name)

        if attribute is None:
            fields = {"content": "```"}

            for key, value in vars(returned_model).items():
                if key.startswith("_"):
                    continue

                fields["content"] += f"{Utils.to_snake_case(key)}: {value}\n"

                if isinstance(value, str) and Utils.is_image(value):
                    if fields.get("files") is None:
                        fields["files"] = []

                    fields["files"].append(discord.File(Utils.image_path(value)))

            fields["content"] += "```"

            await ctx.send(**fields)
            return

        _attr_name = attribute.name.__name__ if attribute.type == Types.MODEL else attribute.name
        
        attribute_name = Utils.casing(_attr_name.lower())

        if not hasattr(model.name(), attribute_name):
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
        model_name = model.name if isinstance(model.name, str) else model.name.__name__

        parameters = f"{model_name.upper()} ATTRIBUTES:\n\n"

        for field in vars(model.name()):  # type: ignore
            if field[:1] == "_":
                continue

            parameters += f"- {Utils.to_snake_case(field).replace(' ', '_').upper()}\n"

        await ctx.send(f"```{parameters}```")


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
        _attr_name = attribute.name.__name__ if attribute.type == Types.MODEL else attribute.name
        casing_name = Utils.casing(_attr_name.lower())

        if not hasattr(model.name(), casing_name):
            self.attribute_error(model, casing_name)

        if tortoise_operator is not None:
            casing_name += f"__{tortoise_operator.name.lower()}"

        value_old = old_value.name
        value_new = new_value.name

        if attribute.type == Types.MODEL:
            value_old = await self.get_model(attribute, value_old)
            value_new = await self.get_model(attribute, value_new)

        await model.name.filter(**{casing_name: value_old}).update(
            **{casing_name: value_new}
        )

        await ctx.send(
            f"Updated all `{model.name.__name__}` instances from a "
            f"`{attribute}` value of `{old_value}` to `{new_value}`"
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
        _attr_name = attribute.name.__name__ if attribute.type == Types.MODEL else attribute.name

        casing_name = Utils.casing(_attr_name.lower())

        if not hasattr(model.name(), casing_name):
            self.attribute_error(model, casing_name)

        if tortoise_operator is not None:
            casing_name += f"__{tortoise_operator.name.lower()}"

        new_value = value.name

        if attribute.type == Types.MODEL:
            new_value = await self.get_model(attribute, new_value)

        await model.name.filter(**{casing_name: new_value}).delete()

        await ctx.send(
            f"Deleted all `{model.name.__name__}` instances with a "
            f"`{attribute}` value of `{value}`"
        )


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
                f"`{name}` is above the {NAME_LIMIT} character limit "
                f"({len(name)} > {NAME_LIMIT})"
            )

        if os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` aleady exists.")

        await ctx.send("Please send the eval command below...")

        try:
            message = await self.bot.wait_for(
                "message", timeout=20, check=lambda m: m.author == ctx.message.author
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
        
        await ctx.send(f"```{'\n'.join(os.listdir("eval_presets"))}```")

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

        await ctx.send(f"```{'\n'.join(os.listdir(path))}```")

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

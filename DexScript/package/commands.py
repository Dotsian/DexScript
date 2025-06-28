import asyncio
import os
import re
import shutil

import discord

from .utils import STATIC, Types, Utils

EMOJI_RE = re.compile(r"^[a-zA-Z0-9_]{2,32}$")


class DexCommand:
    """
    Default class for all dex commands.
    """

    def __init__(self, bot, attachments):
        self.bot = bot
        self.attachments = attachments

    def __loaded__(self):
        """
        Calls whenever the command is loaded for the first time.
        """
        pass

    def attribute_error(self, model, attribute):
        """
        Raises an error if an attribute doesn't exist in a model.

        Parameters
        ----------
        model:
            The model you want to check in.
        attribute:
            The attribute you want to check.
        """
        if model.value is None or hasattr(model.value(), attribute):
            return

        raise Exception(
            f"'{attribute}' is not a valid {model.name} attribute\n"
            f"Run `ATTRIBUTES > {model.name}` to see a list of "
            "all attributes for that model"
        )

    def type_error(self, value, name: str, allowed_types: list[Types]):
        """
        Raises an error if the type of a `Value` is not allowed.

        Parameters
        ----------
        value:
            The value that has the original type.
        name:
            The name of the value.
        allowed_types:
            A list of types that are allowed.
        """
        if value is None or value.type in allowed_types:
            return

        raise Exception(f"'{value.type}' is an invalid type for '{name}'.")


class Global(DexCommand):
    """
    Main methods for DexScript.
    """

    async def create(self, ctx, model, identifier, values=None):
        """
        Creates a model instance.

        Parameters
        -------------
        model:
            The model you want to create an instance for.
        identifier:
            The identifier (name) of the model instance.
        values:
            The values you want to provide to the newly created model instance.

        Documentation
        -------------
        CREATE > MODEL > IDENTIFIER > VALUES(?)
        """
        self.type_error(values, "values", [Types.DICT])
        
        await Utils.create_model(model.value, identifier, values)
        await ctx.send(f"Created `{identifier}` {model.name.lower()}")

    async def delete(self, ctx, model, identifiers):
        """
        Deletes one or multiple model instances.

        Parameters
        -------------
        model:
            The model you want to delete the instance from.
        identifiers:
            The identifier(s) of the instance(s) you want to delete.

        Documentation
        -------------
        DELETE > MODEL > IDENTIFIER(S)
        """
        async def delete_model(identifier):
            fetched_model = await Utils.get_model(model, identifier)

            await fetched_model.delete()

            await ctx.send(f"Deleted `{identifier}` {model.name.lower()}")

        if identifiers.type != Types.ARRAY:
            await delete_model(identifiers)
            return

        for identifier in identifiers.value:
            await delete_model(identifier)

    async def update(self, ctx, model, identifier, attribute, value=None):
        """
        Updates a model instance's attribute.

        Parameters
        -------------
        model:
            The model you want to update the instance from.
        identifier:
            The identifier of the model instance.
        attribute:
            The attribute you want to update.
        value:
            The new value of the specified attribute. If blank, it will search for attachments.

        Documentation
        -------------
        UPDATE > MODEL > IDENTIFIER > ATTRIBUTE > VALUE(?)
        """
        attribute_name = attribute.name.lower()
        new_value = None if value is None else value.value

        returned_model = await Utils.get_model(model, identifier)
        self.attribute_error(model, attribute_name)

        image_fields = Utils.fetch_fields(
            model.value,
            lambda _, field_type: (
                field_type.__class__.__name__ == "CharField" and field_type.max_length == 200
            ),
        )

        if attribute_name in image_fields:
            file = None

            if new_value is not None and new_value.startswith("https://"):
                file = Utils.from_link(new_value)
            else:
                file = self.attachments.pop(0)

            image_path = await Utils.save_file(file)

            new_value = f"/static/uploads/{image_path}" if STATIC else image_path

        if attribute.type == Types.MODEL and value is not None:
            attribute_name = f"{attribute.name.lower()}_id"
            attribute_model = await Utils.get_model(attribute, value)

            new_value = attribute_model.pk

        setattr(returned_model, attribute_name, new_value)
        await returned_model.save(update_fields=[attribute_name])

        suffix = "" if value is None else f" to `{value.name}`" 

        await ctx.send(f"Updated `{identifier}'s` {attribute}{suffix}")

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
                    fields.setdefault(
                        "files", []).append(discord.File(Utils.image_path(value)) # type: ignore
                    )

            fields["content"] += "```"
            await ctx.send(**fields)
            return

        attribute_name = attribute.name.lower()
        self.attribute_error(model, attribute_name)

        new_attribute = getattr(returned_model, attribute_name)

        if isinstance(new_attribute, str) and Utils.is_image(new_attribute):
            await ctx.send(
                f"```{new_attribute}```", file=discord.File(Utils.image_path(new_attribute))
            )
            return

        if attribute.type == Types.MODEL and not isinstance(new_attribute, str):
            new_attribute = await new_attribute.values_list(attribute.extra_data[0], flat=True)

        await ctx.send(f"```{new_attribute}```")

    async def attributes(self, ctx, model, filter=None):
        """
        Lists all changeable attributes of a model.

        Documentation
        -------------
        ATTRIBUTES > MODEL > FILTER(?)
        """
        def filter_function(_, field_type):
            if field_type.__class__.__name__ == "BackwardFKRelation":
                return False
            
            if filter is None:
                return True
            
            match filter.value.lower():
                case "null":
                    return field_type.null
                case "valid":
                    return not field_type.null
            
            return True

        fields = [f"- {x.upper()}" for x in Utils.fetch_fields(model.value, filter_function)]
        fields.insert(0, f"{model.name.upper()} ATTRIBUTES:\n")

        await Utils.message_list(ctx, fields)


class Filter(DexCommand):
    """
    Filter commands used for mass updating, deleting, and viewing models.
    """

    async def update(self, ctx, model, attribute, old_value, new_value, tortoise_operator=None):
        """
        Updates all instances of a model to the specified value where the specified attribute 
        meets the condition defined by the optional `TORTOISE_OPERATOR` argument 
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

        await model.value.filter(**{casing_name: new_value}).delete()

        await ctx.send(
            f"Deleted all `{model.name}` instances with a `{attribute}` value of `{value}`"
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

        instances = await model.value.filter(**{casing_name: new_value}).values_list(
            model.extra_data[0], flat=True
        )

        if instances == []:
            await ctx.send(
                f"No {model.name}s found with a `{attribute}` value of `{value}`"
            )
            return

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

        Parameters
        ----------
        name:
            The name of the eval preset you want to save.

        Documentation
        -------------
        EVAL > SAVE > NAME
        """
        NAME_LIMIT = 100

        if len(name.name) > NAME_LIMIT:
            raise Exception(
                f"`{name}` exceeds the {NAME_LIMIT}-character limit ({len(name)} > {NAME_LIMIT})"
            )

        await ctx.send("Please send the eval command below...")

        try:
            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=20,
            )
        except asyncio.TimeoutError:
            await ctx.send("Eval preset saving has timed out.")
            return

        with open(f"eval_presets/{name}.py", "w") as file:
            file.write(Utils.remove_code_markdown(message.content))

        await ctx.send(f"`{name}` eval preset has been saved!")

    async def file(self, ctx):
        """
        Runs an eval command from a file.

        Documentation
        -------------
        EVAL > FILE
        """
        content = await self.attachments[0].read()

        self.attachments.pop(0)

        await ctx.invoke(self.bot.get_command("eval"), body=content.decode())

    async def remove(self, ctx, name):
        """
        Removes an eval preset.

        Parameters
        ----------
        name:
            The name of the eval preset you want to remove.

        Documentation
        -------------
        EVAL > REMOVE > NAME
        """
        if not os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` does not exists")

        os.remove(f"eval_presets/{name}.py")

        await ctx.send(f"Removed `{name}` preset.")

    async def list(self, ctx):
        """
        Lists all eval presets.

        Documentation
        -------------
        EVAL > LIST
        """
        if os.listdir("eval_presets") == []:
            await ctx.send("You have no eval presets saved.")
            return

        await Utils.message_list(ctx, os.listdir("eval_presets"))

    async def run(self, ctx, name):
        """
        Runs an eval preset.

        Parameters
        ----------
        name:
            The name of the eval preset you want to run.

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

    async def read(self, ctx, file_paths):
        """
        Sends one or more files based on the specified file paths.

        Documentation
        -------------
        FILE > READ > FILE_PATH(S)
        """
        if file_paths.type != Types.ARRAY:
            await ctx.send(file=discord.File(file_paths.name))
            return

        files = []

        for path in file_paths.value:
            files.append(discord.File(path.name))

        await ctx.send(files=files)

    async def write(self, ctx, file_path):
        """
        Writes to a file. If an attachment is added, it will save the attachment.

        Documentation
        -------------
        FILE > WRITE > FILE_PATH
        """
        if self.attachments == []:
            if os.path.isfile(file_path.name):
                raise Exception(f"{file_path} already exists.")
            
            with open(file_path.name, "w"):
                pass

            await ctx.send(f"Created `{file_path}`")
            return
        
        new_file = self.attachments[0]
        
        self.attachments.pop(0)

        await new_file.save(file_path.name)

        await ctx.send(f"Wrote to `{file_path}` from `{new_file.filename}`")

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

    async def mkdir(self, ctx, file_path):
        """
        Creates a new directory.

        Parameters
        -------------
        file_path:
            The file path of the directory.

        Documentation
        -------------
        FILE > MKDIR > FILE_PATH
        """
        os.mkdir(file_path.value)

        await ctx.send(f"Created `{file_path}` directory")

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

    async def create(self, ctx, model, argument="...", include_args=None):
        """
        Sends the `create` template for a model.

        Documentation
        -------------
        TEMPLATE > CREATE > MODEL > ARGUMENT(?) > INCLUDE_ARGS(?)
        """
        def filter_function(field, field_type):
            if field_type.__class__.__name__ in ["BackwardFKRelation", "JSONField"]:
                return False

            if field_type.null or field_type.default or field.endswith("_id"):
                return False

            if field in [model.extra_data[0], "id"]:
                return False

            return True

        args = [x.upper() for x in Utils.fetch_fields(model.value, filter_function)]

        structure = f"UPDATE > {model.name.upper()} > {argument} > $value > ..."
        template_commands = [f"CREATE > {model.name.upper()} > {argument}"]

        if include_args is not None:
            args += [x.name.upper() for x in include_args.value]

        for arg in args:
            template_commands.append(structure.replace("$value", arg))

        await ctx.send(f"```sql\n{'\n'.join(template_commands)}\n```")

class Emoji(DexCommand):
    """
    Commands used for modifying application emojis.
    """

    async def new(self, ctx, name, image=None):
        """
        Creates an application emoji based on the provided image and name.

        Parameters
        -------------
        name:
            The name of the emoji you want to create.
        image:
            The image link you want to use if there are no attachments.

        Documentation
        -------------
        EMOJI > NEW > NAME > IMAGE(?)
        """
        image_content = None
        
        if image is None:
            image_content = await self.attachments[0].read()

            self.attachments.pop(0)
        else:
            image_content = Utils.from_link(image.value)[1]

        new_name = name.value.replace(" ", "").replace('"', "")

        if not bool(EMOJI_RE.match(new_name)):
            raise Exception(f"Emoji name `{new_name}` is invalid.")

        emoji = await self.bot.create_application_emoji(name=new_name, image=image_content)

        await ctx.send(f"Created {emoji} **{new_name}** `({emoji.id})`")

    async def delete(self, ctx, name):
        """
        Deletes an application emoji.

        Parameters
        -------------
        name:
            The name of the emoji you want to delete.

        Documentation
        -------------
        EMOJI > DELETE > NAME
        """
        emojis = await self.bot.fetch_application_emojis()
        new_name = name.value.replace(" ", "").replace('"', "")

        emoji = discord.utils.get(emojis, name=new_name)

        if not emoji.is_application_owned():
            raise Exception("This emoji is not owned by the application.")

        await ctx.send(f"Deleted {emoji} **{new_name}**")

        await emoji.delete()

    async def info(self, ctx, name):
        """
        Displays information about an application emoji.

        Parameters
        -------------
        name:
            The name of the emoji you want to view.

        Documentation
        -------------
        EMOJI > INFO > NAME
        """
        emojis = await self.bot.fetch_application_emojis()
        new_name = name.value.replace(" ", "").replace('"', "")

        emoji = discord.utils.get(emojis, name=new_name)

        if not emoji.is_application_owned():
            raise Exception("This emoji is not owned by the application.")
        
        await ctx.send(f"{emoji} **{new_name}**\nID: `{emoji.id}`")

import asyncio
import os
import requests
import shutil
from base64 import b64decode

import discord

from .utils import Utils, MEDIA_PATH


class DexCommand:
    def __init__(self, bot):
        self.bot = bot

    def __loaded__(self):
        pass

    async def create_model(self, model, identifier):
        fields = {}
        
        special_list = {k: Utils.port(v) for k, v in {
            "Identifiers": ["country", "catch_names", "name"],
            "Ignore": ["id", "short_name"]
        }.items()}

        for field, field_type in model._meta.fields_map.items():
            if vars(model()).get(field) is not None or field in special_list["Ignore"]:
                continue

            if field in special_list["Identifiers"]:
                fields[field] = identifier
                continue

            match field_type:
                case "ForeignKeyFieldInstance":
                    pass
                    # instance = await Models.fetch_model(field).first()
                    
                    # if instance is None:
                        # raise Exception(f"Could not find default {field}")
                    
                    # fields[field] = instance.pk

                case "BigIntField":
                    fields[field] = 100 ** 8

                case "BackwardFKRelation" | "JSONField":
                    continue

                case _:
                    fields[field] = 1

        await model.create(**fields)

    async def get_model(self, model, identifier):
        attribute = Utils.extract_str_attr(model.name)

        correction_list = await model.name.all().values_list(attribute, flat=True)
        translated_identifier = Utils.port(model.extra_data[0].lower())

        try:
            returned_model = await model.name.filter(
                **{
                    translated_identifier: Utils.autocorrect(identifier, correction_list)
                }
            )
        except AttributeError:
            raise Exception(f"'{model}' is not a valid model.")

        return returned_model[0]


class Global(DexCommand):
    """
    Main methods for DexScript.
    """

    async def help(self, ctx):
        """
        Lists all DexScript commands and provides documentation for them.

        Documentation
        -------------
        HELP
        """
        # getattr(Methods, command).__doc__.replace("\n", "").split("Documentation-------------")
        pass

    async def create(self, ctx, model, identifier):
        """
        Creates a model instance.

        Documentation
        -------------
        CREATE > MODEL > IDENTIFIER
        """
        await self.create_model(model.name, identifier)

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
        new_attribute = value.name if value is not None else None

        if value is None:
            image_path = await Utils.save_file(ctx.message.attachments[0])
            new_attribute = f"{MEDIA_PATH}/{image_path}"

        await self.get_model(model, identifier.name).update(
            **{attribute.name.lower(): new_attribute}
        )

        await ctx.send(f"Updated `{identifier}'s` {attribute} to `{new_attribute}`")


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

                fields["content"] += f"{key}: {value}\n"

                if isinstance(value, str) and Utils.is_image(value):
                    if fields.get("files") is None:
                        fields["files"] = []
                    
                    fields["files"].append(discord.File(value[1:]))

            fields["content"] += "```"

            await ctx.send(**fields)
            return

        new_attribute = getattr(returned_model, attribute.name.lower())

        if isinstance(new_attribute, str) and os.path.isfile(new_attribute[1:]):
            await ctx.send(f"```{new_attribute}```", file=discord.File(new_attribute[1:]))
            return

        await ctx.send(f"```{new_attribute}```")


    async def attributes(self, ctx, model):
        """
        Lists all changeable attributes of a model.

        Documentation
        -------------
        ATTRIBUTES > MODEL
        """
        model_name = (
            model.name if isinstance(model.name, str) else model.name.__name__
        )

        parameters = f"{model_name.upper()} ATTRIBUTES:\n\n"

        for field in vars(model.name()):  # type: ignore
            if field[:1] == "_":
                continue

            parameters += f"- {field.replace(' ', '_').upper()}\n"

        await ctx.send(f"```{parameters}```")


class Filter(DexCommand):
    """
    Filter commands used for mass updating, deleting, and viewing models.
    """

    # TODO: Add attachment support.
    async def update(
        self, ctx, model, attribute, old_value, new_value, tortoise_operator=None
    ):
        """
        Updates all instances of a model to the specified value where the specified attribute 
        meets the condition  defined by the optional `TORTOISE_OPERATOR` argument 
        (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER > UPDATE > MODEL > ATTRIBUTE > OLD_VALUE > NEW_VALUE > TORTOISE_OPERATOR(?)
        """
        lower_name = attribute.name.lower()

        if tortoise_operator is not None:
            lower_name += f"__{tortoise_operator.name.lower()}"

        await model.name.filter(**{lower_name: old_value.name}).update(
            **{lower_name: new_value.name}
        )

        await ctx.send(
            f"Updated all `{model}` instances from a "
            f"`{attribute}` value of `{old_value}` to `{new_value}`"
        )


    async def delete(
        self, ctx, model, attribute, value, tortoise_operator=None
    ):
        """
        Deletes all instances of a model where the specified attribute meets the condition 
        defined by the optional `TORTOISE_OPERATOR` argument 
        (e.g., greater than, equal to, etc.).

        Documentation
        -------------
        FILTER > DELETE > MODEL > ATTRIBUTE > VALUE > TORTOISE_OPERATOR(?)
        """
        lower_name = attribute.name.lower()
        
        if tortoise_operator is not None:
            lower_name += f"__{tortoise_operator.name.lower()}"
        
        await model.name.filter(**{lower_name: value.name}).delete()

        await ctx.send(
            f"Deleted all `{model}` instances with a "
            f"`{attribute}` value of `{value}`"
        )


class Eval(DexCommand):
    """
    Developer commands for executing evals.
    """

    def __loaded__(self):
        os.makedirs("eval_presets", exist_ok=True)


    async def exec_git(self, ctx, link):
        link = link.split("/")
        start = f"{link[0]}/{link[1]}"

        link.pop(0)
        link.pop(0)

        api = f"https://api.github.com/repos/{start}/contents/{'/'.join(link)}"
        
        request = requests.get(api)

        if request.status_code != requests.codes.ok:
            raise Exception(f"Request Error Code {request.status_code}")

        content = b64decode(request.json()["content"])

        try:
            await ctx.invoke(self.bot.get_command("eval"), body=content.decode("UTF-8"))
        except Exception as error:
            raise Exception(error)
        else:
            await ctx.message.add_reaction("✅")
            

    async def save(self, ctx, name):
        if len(name.name) > 25:
            raise Exception(f"`{name}` is above the 25 character limit.")
        
        if os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` aleady exists.")

        await ctx.send("Please paste the eval command below...")

        try:
            message = await self.bot.wait_for(
                "message", timeout=15, check=lambda m: m.author == ctx.message.author
            )
        except asyncio.TimeoutError:
            await ctx.send("Preset saving has timed out.")
            return
        with open(f"eval_presets/{name}.py", "w") as file:
            file.write(Utils.remove_code_markdown(message.content))

        await ctx.send(f"`{name}` eval preset has been saved!")


    async def remove(self, ctx, name):
        if not os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` does not exists.")

        os.remove(f"eval_presets/{name}.py")

        await ctx.send(f"Removed `{name}` preset.")


    async def run(self, ctx, name): # TODO: Allow args to be passed through `run`.
        if not os.path.isfile(f"eval_presets/{name}.py"):
            raise Exception(f"`{name}` does not exists.")

        with open(f"eval_presets/{name}.py", "r") as file:
            try:
                await ctx.invoke(self.bot.get_command("eval"), body=file.read())
            except Exception as error:
                raise Exception(error)
            else:
                await ctx.message.add_reaction("✅")


class File(DexCommand):
    """
    Developer commands for managing and modifying the bot's internal filesystem.
    """

    async def read(self, ctx, file_path):
        await ctx.send(file=discord.File(file_path.name))

            
    async def write(self, ctx, file_path):
        new_file = ctx.message.attachments[0]

        with open(file_path.name, "w") as opened_file:
            contents = await new_file.read()
            opened_file.write(contents.decode("utf-8"))

        await ctx.send(f"Wrote to `{file_path}`")


    async def clear(self, ctx, file_path):
        if not os.path.isfile(file_path):
            raise Exception(f"'{file_path}' does not exist")
        
        with open(file_path.name, "w") as _:
            pass

        await ctx.send(f"Cleared `{file_path}`")


    async def listdir(self, ctx, file_path=None):
        path = file_path.name if file_path is not None else None

        await ctx.send(f"```{'\n'.join(os.listdir(path))}```")
        

    async def delete(self, ctx, file_path):
        is_dir = os.path.isdir(file_path.name)

        file_type = "directory" if is_dir else "file"

        if is_dir:
            shutil.rmtree(file_path.name)
        else:
            os.remove(file_path.name)

        await ctx.send(f"Deleted `{file_path}` {file_type}")

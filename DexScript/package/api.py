from .utils import Types


class DexCommand:
    """
    Default class for all dex commands.
    """

    def __init__(self, bot, shared):
        self.bot = bot
        self.shared = shared

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
        model: Value
            The model you want to check in.
        attribute: Value
            The attribute you want to check.
        """
        if model.value is None or hasattr(model.value(), attribute):
            return

        raise Exception(
            f"'{attribute}' is not a valid {model.name} attribute\n"
            f"Run `ATTRIBUTES > {model.name}` to see a list of "
            "all attributes for that model"
        )

    def type_error(self, value, allowed_types: list[Types]):
        """
        Raises an error if the type of a `Value` is not allowed.

        Parameters
        ----------
        value: Value
            The value that has the original type.
        allowed_types: list[Types]
            A list of types that are allowed.
        """
        if value.type in allowed_types:
            return

        raise Exception(f"'{value.type}' is an invalid type.")

class ModelNotDeclaredError(Exception):
    """
    Gets raised when a command requires a model declaration.
    """

    def __init__(self, identifier: str, models: list[str]):
        models = ", ".join(models)

        super().__init__(
            f"'{identifier}' was found in multiple models, such as {models}\n"
            "Please explicitly declare the model before running this command "
            f"(e.g. BALL > EDIT > {identifier} > ...)"
        )

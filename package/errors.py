class ModelNotDeclaredError(Exception):
    """
    Gets raised when a command requires a model declaration.
    """

    def __init__(self, identifier: str, models: list[str]):
        model_list = ", ".join(models)

        super().__init__(
            f"'{identifier}' was found in multiple models, such as {model_list}\n"
            "Please explicitly declare the model before running this command "
            f"(e.g. BALL > EDIT > {identifier} > ...)"
        )

from package.command import Extension, load_extensions


def test_classes():
    """
    Ensures all extensions found are a subclass of `Extension`
    """
    for extension in load_extensions():
        assert issubclass(extension, Extension)


def test_commands():
    """
    Ensures extensions have at least one command.
    """
    for extension in load_extensions():
        assert hasattr(extension, "commands") and len(extension.commands) > 0

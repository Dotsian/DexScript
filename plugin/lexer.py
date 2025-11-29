from pygments.lexer import RegexLexer
from pygments.token import Comment, Keyword, Name, Number, Operator, Text

from .settings import ATTRIBUTES, METHODS, MODELS

KEYWORDS = "|".join(METHODS + MODELS)
KEYATTRS = "|".join(ATTRIBUTES)


class DexScriptLexer(RegexLexer):
    """
    A lexer that adds support for the DexScript language.
    """

    name = "DexScript"
    aliases = ["ds", "dexscript"]
    filenames = ["*.ds"]

    tokens = {
        "root": [
            # Comments
            (r"--.*?$", Comment.Single),
            # Attributes
            (rf"(?<!\w)(?:{KEYATTRS})(?:-[A-Za-z0-9_]+)?", Name.Label),
            # Commands & Models
            (rf"(?<!\w)(?:{KEYWORDS})(?:-[A-Za-z0-9_]+)?", Keyword),
            # Separators
            (r">", Operator),  # Separator
            (r"^\|", Operator),  # Chain
            # Numbers & Hex
            (r"#?\d+(\.\d+)?", Number),
            # Booleans
            (r"\b(True|False)\b(?!-)", Name.Constant),
            # Placeholders
            (r"\[[^\]]*\]", Name.Attribute),
            # Identifiers
            (r"[A-Za-z_][A-Za-z0-9_]*", Name),
            # Whitespace
            (r"\s+", Text),
            # Fallback
            (r".", Text),
        ]
    }

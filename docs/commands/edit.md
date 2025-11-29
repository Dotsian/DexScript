# Edit

**Edit** is a model declarative command used to change a model instance's attribute. If you wanted to change a ball's health, you would use this command.

=== "Default"

    ```ds
    EDIT > [MODEL-NAME] > [ATTRIBUTE] > [VALUE]
    ```

    - `MODEL-NAME` - The identifier of the model instance you want to modify.
    - `ATTRIBUTE` - The attribute you want to edit.
    - `VALUE` - The new value to assign to the attribute.

=== "ATTR"

    ```ds
    EDIT-ATTR > [ATTRIBUTE]
    | [MODEL-NAME] > [VALUE]
    ```

    - `ATTRIBUTE` - The attribute you want to edit across all instances.
    - `MODEL-NAME` - The identifier of the model instance you want to modify.
    - `VALUE` - The new value to assign to the attribute.

=== "MULTI"

    ```ds
    EDIT-MULTI > [ATTRIBUTE] > [VALUE]
    | [MODEL-NAME]
    ```

    - `ATTRIBUTE` - The attribute you want to edit across all instances.
    - `VALUE` - The new value to assign across all attributes.
    - `MODEL-NAME` - The identifier of the model instance you want to modify.

=== "FILTER"

    !!! note

        `EDIT-FILTER` requires a model to be specified.

    ```ds
    EDIT-FILTER > [MODEL] > [ATTRIBUTE] > [OLD-VALUE] > [NEW-VALUE]
    ```

    - `MODEL` - The model you want to use.
    - `ATTRIBUTE` - The attribute whose value you want to search and replace.
    - `OLD-VALUE` - The value to look for when filtering model instances.
    - `NEW-VALUE` - The value to assign to all matching instances.


## Operations

- **ATTR** - Declares a single attribute first, then edits its value across multiple model instances.
- **MULTI** - Defines a single attribute and value, then applies that value to all listed model instances.
- **FILTER** - Edits all model instances from one value to another.

## Examples

=== "Default"

    Editing Ancient Greece's health without model declaration:

    ```ds
    EDIT > Ancient Greece > HEALTH > 1000
    ```

    Editing Ancient Greece's health with model declaration:

    ```ds
    EDIT > BALL > Ancient Greece > HEALTH > 1000
    ```

    Editing Ancient Greece's attack and health:

    ```ds
    EDIT > Ancient Greece
    | HEALTH > 1000
    | ATTACK > 500
    ```

=== "ATTR"

    Editing Ancient Greece and Sparta's health:

    ```ds
    EDIT-ATTR > HEALTH
    | Ancient Greece > 1000
    | Sparta > 1200
    ```

=== "MULTI"

    Editing Ancient Greece, Sparta, and Northern Cyprus's rarity:

    ```ds
    EDIT-MULTI > RARITY > 4.0
    | Ancient Greece
    | Sparta
    | Northern Cyprus
    ```

    Editing Italy and Bulgaria's credits:

    ```ds
    EDIT-MULTI > CREDITS > Silly (Spawn & Card)
    | Italy
    | Bulgaria
    ```

=== "FILTER"

    Editing all balls with a certain rarity value:

    ```ds
    EDIT-FILTER > BALL > RARITY > 4.0 > 5.0
    ```

    Transferring all balls from one user to another:

    ```ds
    EDIT-FILTER > BALL-INSTANCE > PLAYER > 999736048596816014 > 348415857728159745
    ```

    Disabling all balls:

    ```ds
    EDIT-FILTER > BALL > ENABLED > True > False
    ```

*[model declarative]: A model declarative command is a command that performs an operation on a model or a model instance. These commands can usually determine which model they need to access automatically, but in some cases they require the model to be explicitly specified.
# Delete

**Delete** is a [global](../extensions/global.md) model declarative command used to delete a model instance. If you wanted to delete a ball, you would use this command.

```ds
DELETE > [MODEL-NAME]
```

- `MODEL-NAME` - The identifier of the model instance you want to delete.

## Examples

Deleting Cyprus without model declaration:

```ds
DELETE > Cyprus
```

Deleting Roman Empire with model declaration:

```ds
BALL > DELETE > Roman Empire
```

*[model declarative]: A model declarative command is a command that performs an operation on a model or a model instance. These commands can usually determine which model they need to access automatically, but in some cases they require the model to be explicitly specified.

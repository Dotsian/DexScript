# Types

Types define how values are interpreted and used in DexScript. Every value has a type, which determines how it is parsed, stored, and interacted with during execution.

Some types (Common Types) can be inferred multiple times, while others (Parsing Types) are only determined once during parsing.

## Common Types

A **common type** is a type that can be inferred multiple times.

### STRING

A **string** is a sequence of characters. If a value's type could not be determined, it defaults to a string.

```ds
... > Hello World!
```

### BOOLEAN

A **boolean** is a logical type that has exactly two values, **True** or **False**.

```ds
... > True
... > False
```

### DATETIME

A **datetime** represents a calendar date. It is created using the ISO 8601 format `(YYYY-MM-DD)`.

```ds
... > 2025-12-16
```

### HEX

A **hexadecimal** value is a base-16 number. It is created by prefixing a value with a `#`.

```ds
... > #11C
```

### ARRAY

An **array** is a collection that can hold multiple values of any type. Arrays are defined using square brackets (`[]`).

```ds
... > [Hello World, False, $N]
```

### MODEL

A **model** represents a Ballsdex-specific model type.

```ds
... > BALL
... > SPECIAL
```

### NONE

The **none** type represents the absence of a value. It is created using `$N`.

```ds
... > $N
```

## Parsing Types

A parsing type is a type that can only be inferred once during parsing.

### EXTENSION

An **extension** represents a class defined in DexScript. It is identified by its name and is not treated as a string.

```ds
FILE > ...
```

### COMMAND

A **command** is a function defined within an extension. It is identified by its name and is not treated as a string.

```ds
... > WRITE > ...
```

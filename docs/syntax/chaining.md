# Chaining

Chaining lets you write cleaner and faster arguments by piping values directly into a command instead of repeating the full command every time.

## Without chaining

```ds
EDIT > Ancient Greece > RARITY > 4.0
EDIT > Sparta > RARITY > 4.0
EDIT > Northern Cyprus > RARITY > 4.0
EDIT > Ancient Troy > RARITY > 4.0
EDIT > Roman Empire > RARITY > 4.0
EDIT > Kingdom of Greece > RARITY > 4.0
```

## With chaining

```ds
EDIT-MULTI > RARITY > 4.0
| Ancient Greece
| Sparta
| Northern Cyprus
| Ancient Troy
| Roman Empire
| Kingdom of Greece
```

Using chaining makes your code less repetitive and makes it faster to write.

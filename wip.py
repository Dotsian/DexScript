from dataclasses import dataclass, field


#@dataclass
class Migration:
    def __init__(self):
        self.header: str = ""
        self.upgrade: dict = {}
        self.drop: list = []
    
dir_type = "ballsdex"

class Migrations:
    @staticmethod
    def load(migrations):
        new_migration = Migration()
        current_migration = ""
        
        def format_migration(line):
            return (
                line.replace("    ", "")
                .replace("/-", "    ")
                .replace(" -n", "\n")
                .replace("$DIR", dir_type)
            )
        
        for line in migrations.split("\n"):
            if line.startswith("@ ->"):
                new_migration.header = line.replace("@ ->", "").strip()
                
            if line == "":
                current_migration = ""
                
            if current_migration == "Drop":
                new_migration.drop.append(
                    format_migration(line)
                )
                
            if current_migration != "" and "||" in line:
                items = format_migration(line).split(" || ")
                attr = getattr(new_migration, current_migration.lower())
                attr[items[0]] = items[1]
                setattr(new_migration, current_migration.lower(), attr)
                
            if line[:-1] in ["Upgrade", "Drop"]:
                current_migration = line[:-1]
                print(current_migration)
                
        return new_migration
        
    @staticmethod
    def migrate(migration, file):
        lines = text.split("\n")
        contents = ""

        for index, line in enumerate(lines):
            if line in migration.drop:
                continue

            contents += line + "\n"

            for key, item in migration.upgrade.items():
                if line.rstrip() != key or lines[index + 1] == item:
                    continue                
                
                contents += item
                
migration = Migrations.load("""
@ -> ballsdex/packages/countryballs/component.py

Upgrade:
-
    import types 
-
    import 0s -n
-

Drop:
-
    from ballsdex.core.dexscript import DexScript -n
-
""")

print(migration.header)
from supabase import Client

def updateDatabase(supabase: Client, update: dict):
    updated = {}
    for nation, changes in update.items():
        updated[nation] = {}
        for column, operation in changes.items():
            res = supabase.table("nations").select(column).eq("Name", nation).execute()
            if not res.data:
                raise ValueError(f"Nation '{nation}' not found")

            current_value = res.data[0][column]
            if operation.type == "add":
                if operation.key is not None:
                    current_value[operation.key] = current_value.get(operation.key, 0) + operation.value
                    newval = current_value
                else:
                    newval = current_value + operation.value
            elif operation.type == "set":
                if operation.key is not None:
                    current_value[operation.key] = operation.value
                    newval = current_value
                else:
                    newval = operation.value
            else:
                raise ValueError("Invalid operation type.")

            supabase.table("nations").update({column: newval}).eq("Name", nation).execute()

            updated[nation][column] = newval

    return updated
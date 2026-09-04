from supabase import Client

def updateDatabase(supabase: Client, update: dict):
    updated = {}
    for nation, changes in update.items():
        updated[nation] = {}
        for column, operation in changes.items():
            if operation.type == "add":
                amount = operation.value

                res = supabase.table("nations").select(column).eq("Name", nation).execute()

                if not res.data:
                    raise ValueError(f"Nation '{nation}' not found")

                current_value = res.data[0][column]
                newval = current_value + amount
            elif operation.type == "set":
                newval = operation.value  
            else:
              raise ValueError("Invalid operation type.")
            supabase.table("nations").update({column: newval}).eq("Name", nation).execute()
            updated[nation][column] = newval
    return updated
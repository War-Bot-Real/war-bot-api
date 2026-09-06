from supabase import Client

def updateDatabase(supabase: Client, updates: list):
    updated = []

    for update in updates:

        table = update["table"]
        where = update["where"]
        changes = update["changes"]

        # Find the row
        query = supabase.table(table).select("*")

        for column, value in where.items():
            query = query.eq(column, value)

        res = query.execute()

        if not res.data:
            raise ValueError(
                f"Row not found in table '{table}'"
            )

        current = res.data[0]

        new_values = {}

        # Calculate new values
        for column, operation in changes.items():

            current_value = current[column]

            if operation.type == "add":

                if operation.key is not None:
                    current_value[operation.key] = (
                        current_value.get(operation.key, 0)
                        + operation.value
                    )

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

            new_values[column] = newval

        # Apply all changes to this row at once
        query = supabase.table(table).update(new_values)

        for column, value in where.items():
            query = query.eq(column, value)

        query.execute()

        updated.append({
            "table": table,
            "where": where,
            "changes": new_values
        })

    return updated
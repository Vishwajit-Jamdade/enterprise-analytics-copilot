from .databricks_tool import run_databricks_query

def describe_table(table_name: str) -> str:
    """
    Returns schema for a table.
    Automatically qualifies table with gold schema.
    """

    if "." not in table_name:
        table_name = f"gold.{table_name}"

    query = f"DESCRIBE {table_name}"

    return run_databricks_query(query)
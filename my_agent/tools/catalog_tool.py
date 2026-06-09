from .databricks_tool import run_databricks_query

def get_available_tables() -> str:

    query = """
    SHOW TABLES IN gold
    """

    result = run_databricks_query(query)

    return result.replace(
        "tableName='",
        "tableName='gold."
    )
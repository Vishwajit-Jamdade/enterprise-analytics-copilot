# import os
# from databricks import sql
# from dotenv import load_dotenv

# load_dotenv()

# def run_databricks_query(query: str) -> str:
#     """
#     Execute SQL query against Databricks SQL Warehouse.
#     """

#     print(f"Executing SQL: {query}")

#     with sql.connect(
#         server_hostname=os.getenv("DATABRICKS_HOST"),
#         http_path=os.getenv("DATABRICKS_HTTP_PATH"),
#         access_token=os.getenv("DATABRICKS_TOKEN")
#     ) as conn:

#         with conn.cursor() as cursor:
#             cursor.execute(query)
#             rows = cursor.fetchall()
#             return str(rows)

import os
from databricks import sql
from dotenv import load_dotenv

load_dotenv()


def run_databricks_query(query: str) -> str:
    """
    Execute SQL query against Databricks SQL Warehouse.
    """

    try:
        print("=" * 50)
        print("DATABRICKS TOOL INVOKED")
        print(f"SQL: {query}")
        print("=" * 50)

        with sql.connect(
            server_hostname=os.getenv("DATABRICKS_HOST"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        ) as conn:

            with conn.cursor() as cursor:
                cursor.execute(query)

                rows = cursor.fetchall()

                if not rows:
                    return "No records found."

                return str(rows)

    except Exception as e:
        return f"Error executing query: {str(e)}"
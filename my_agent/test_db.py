# from tools.databricks_tool import run_databricks_query

# result = run_databricks_query(
#     "SELECT COUNT(*) AS total_rows FROM gold.fact_sales"
# )

# print(result)

def run_databricks_query(query: str) -> str:

    print("################################")
    print("TOOL CALLED")
    print(query)
    print("################################")

    ...
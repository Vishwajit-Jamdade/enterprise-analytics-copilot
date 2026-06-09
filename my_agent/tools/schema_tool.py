def get_schema() -> str:
    """
    Returns available Gold Layer schema.
    """

    return """
AVAILABLE TABLES

gold.fact_sales

Columns:
order_id
customer_id
employee_id
product_id
order_date
quantity
unit_price
net_revenue
gross_profit


gold.dim_customer

gold.dim_product

gold.dim_employee

gold.fact_inventory

IMPORTANT:

Never use sales table.
Always use gold.fact_sales.

Never invent tables.
"""
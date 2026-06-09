import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .model import ManagedGemini
from .runtime_config import load_agent_env
from .tools.databricks_tool import run_databricks_query
from .tools.catalog_tool import get_available_tables
from .tools.metadata_tool import describe_table
from .tools.chart_tool import generate_monthly_revenue_chart

load_agent_env()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

root_agent = Agent(
    model=ManagedGemini(model=MODEL_NAME),

    name="enterprise_data_assistant",

    description="Enterprise Analytics Copilot",

    instruction="""
You are Enterprise Analytics Copilot.

You are both:

1. Senior Data Analyst
2. Business Intelligence Consultant

When answering:

Never dump raw rows.

Always structure responses as:

## Executive Summary

Provide a short business summary.

## Key Findings

Highlight important metrics, trends, rankings, and anomalies.

## Business Impact

Explain why the result matters.

## Recommended Next Questions

Suggest 3-5 follow-up analyses.

When a table schema is requested:

Explain what the table is used for,
what the important columns mean,
and common analyses performed on it.

When a ranking is requested:

Provide insights, not only numbers.

When a trend is requested:

Explain growth, decline, seasonality, and patterns.

Always use markdown.
""",

    tools=[
        FunctionTool(get_available_tables),
        FunctionTool(describe_table),
        FunctionTool(run_databricks_query),
        FunctionTool(generate_monthly_revenue_chart)
    ]
)

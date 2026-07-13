"""
evaluate_sql.py — SQL generation accuracy eval for DashQL
Tests only planner + sql_generator, bypassing governance/execution/
visualization/insights entirely — cheaper and more precise.

Run: python evaluate_sql.py
"""

import pandas as pd
from agents.planner import create_dashboard_plan
from agents.sql_generator import generate_sql
from tools.check_schema import get_full_schema
from tools.database import execute_sql

SQL_ACCURACY_TESTS = [
    {
        "question": "How many orders came from Germany?",
        "expected_sql": """
            SELECT COUNT(*) FROM Orders
            JOIN Customers ON Orders.CustomerID = Customers.CustomerID
            WHERE Customers.Country = 'Germany'
        """
    },
    {
        "question": "How many unique customers are there?",
        "expected_sql": "SELECT COUNT(DISTINCT CustomerID) FROM Customers"
    },
    {
        "question": "Which country has the most customers?",
        "expected_sql": """
            SELECT Country, COUNT(*) AS CustomerCount
            FROM Customers
            GROUP BY Country
            ORDER BY CustomerCount DESC
            LIMIT 1
        """
    },
    {
        "question": "How many products are there in total?",
        "expected_sql": "SELECT COUNT(*) FROM Products"
    },
    {
        "question": "What is the total number of orders placed?",
        "expected_sql": "SELECT COUNT(*) FROM Orders"
    },
    {
        "question": "How many employees are there?",
        "expected_sql": "SELECT COUNT(*) FROM Employees"
    },
    {
        "question": "How many products are there in the Beverages category?",
        "expected_sql": """
            SELECT COUNT(*) FROM Products
            JOIN Categories ON Products.CategoryID = Categories.CategoryID
            WHERE Categories.CategoryName = 'Beverages'
        """
    },
    {
        "question": "How many suppliers are there?",
        "expected_sql": "SELECT COUNT(*) FROM Suppliers"
    },
]


def normalize_result(df):
    if df.empty:
        return df
    return df.sort_values(by=list(df.columns)).reset_index(drop=True)


def run_sql_accuracy_eval():
    print("=" * 60)
    print("SQL GENERATION ACCURACY EVAL")
    print("=" * 60)

    schema = get_full_schema()
    correct = 0
    total = len(SQL_ACCURACY_TESTS)
    results = []

    for i, test in enumerate(SQL_ACCURACY_TESTS, 1):
        question = test["question"]
        expected_sql = test["expected_sql"]

        print(f"\n[{i}/{total}] {question}")

        try:
            expected_df = execute_sql(expected_sql)
            expected_normalized = normalize_result(expected_df)
        except Exception as e:
            print(f"  ⚠️ Expected SQL itself failed to run: {e}")
            results.append({"question": question, "passed": False, "reason": "expected_sql_error"})
            continue

        try:
            plan = create_dashboard_plan(question, schema)          # LLM call 1
            components = generate_sql(plan, schema)                  # LLM call 2

            if not components:
                print("  ❌ No SQL generated")
                results.append({"question": question, "passed": False, "reason": "no_sql"})
                continue

            generated_sql = components[0]["sql"]
            actual_df = execute_sql(generated_sql)
            actual_normalized = normalize_result(actual_df)

            match = (
                actual_normalized.shape == expected_normalized.shape
                and (actual_normalized.values == expected_normalized.values).all()
            )

            if match:
                print("  ✅ Match")
                correct += 1
                results.append({"question": question, "passed": True})
            else:
                print(f"  ❌ Mismatch — expected {expected_normalized.values.tolist()}, got {actual_normalized.values.tolist()}")
                print(f"     Generated SQL: {generated_sql}")
                results.append({"question": question, "passed": False, "reason": "value_mismatch"})

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"question": question, "passed": False, "reason": str(e)})

    accuracy = (correct / total) * 100 if total > 0 else 0
    print("\n" + "=" * 60)
    print(f"SQL ACCURACY: {correct}/{total} correct ({accuracy:.1f}%)")
    print("=" * 60)
    return {"correct": correct, "total": total, "accuracy": accuracy, "details": results}


if __name__ == "__main__":
    run_sql_accuracy_eval()
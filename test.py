# test_retrieval.py

from nodes.retreival import search_dashboard, index_dashboard

# Step 1: index a fake dashboard
index_dashboard("dashboard_1", "show me monthly sales")
print("Indexed dashboard_1")

# Step 2: search with the EXACT same text — should match
result = search_dashboard("show me monthly sales")
print("Exact match search result:", result)

# Step 3: search with a SIMILAR but not identical phrasing — should still match
result = search_dashboard("what were the monthly sales figures")
print("Similar phrasing search result:", result)

# Step 4: search with something UNRELATED — should NOT match
result = search_dashboard("what is the capital of France")
print("Unrelated search result:", result)
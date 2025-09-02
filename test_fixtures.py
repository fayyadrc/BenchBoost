#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, 'backend')

import backend.app as app_module

# Test the team fixture queries
queries = [
    "Who is Liverpool facing in GW4",
    "Who is United facing in GW4", 
    "Liverpool fixtures GW4",
    "Who is Manchester United playing in GW4",
    "Who is City facing in GW4",
    "Arsenal fixtures GW4",
    "Who is Chelsea playing GW4"
]

for query in queries:
    print(f"\n=== TESTING: {query} ===")
    try:
        result = app_module.analyze_user_query(query, None)
        print(result)
    except Exception as e:
        print(f"ERROR: {e}")
    print("="*50)

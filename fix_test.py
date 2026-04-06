#!/usr/bin/env python3
from pathlib import Path

tests_dir = Path(__file__).parent / "tests"

# Fix vectorstore_test_full_workflow.py
file1 = tests_dir / "vectorstore_test_full_workflow.py"
content = file1.read_text(encoding="utf-8")

# Fix field name: title -> name
content = content.replace("results[0]['title']", "results[0]['name']")

# Fix file path check
content = content.replace(".vectorstore/workflow.py", ".vectorstore/core/workflow.py")

file1.write_text(content, encoding="utf-8")
print("Fixed vectorstore_test_full_workflow.py")

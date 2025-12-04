#!/usr/bin/env python3
"""Script to add workflow_db_session_factory parameter to test functions."""

import re

# Read the file
with open("tests/integration/test_epic_2_workflow_integration.py", "r") as f:
    content = f.read()

# Pattern to match test functions that have db_session parameter but not workflow_db_session_factory
# and that call create_email_workflow
pattern = r'(async def test_\w+\(\s*self,\s*db_session: AsyncSession,)(\s*test_user:)'

# Replacement: add workflow_db_session_factory parameter after db_session
replacement = r'\1\n        workflow_db_session_factory,\2'

# Apply the replacement
modified_content = re.sub(pattern, replacement, content)

# Write back
with open("tests/integration/test_epic_2_workflow_integration.py", "w") as f:
    f.write(modified_content)

print("Added workflow_db_session_factory parameter to test functions")

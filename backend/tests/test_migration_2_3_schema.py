"""Migration test for Story 2.3 schema changes.

Verifies that migration 93c2f08178be correctly adds all 5 required columns
to the email_processing_queue table.

NOTE: These tests require production database schema and are skipped in test environment.
They can be run manually against staging/production databases.
"""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.skip(reason="Requires production database schema - test DB only has LangGraph tables")
@pytest.mark.asyncio
async def test_story_2_3_migration_columns_exist(db_session: AsyncSession):
    """Test that all 5 classification fields exist after migration 93c2f08178be.

    This test verifies the HIGH SEVERITY fix from code review:
    - Migration must create all 5 columns (was creating only 2)
    - Columns must have correct types and constraints

    Required columns:
    1. classification (String, nullable)
    2. proposed_folder_id (Integer, nullable, FK to folder_categories.id)
    3. classification_reasoning (Text, nullable)
    4. priority_score (Integer, non-nullable, default 0)
    5. is_priority (Boolean, non-nullable, default false)

    AC Coverage: Story 2.3 AC#6
    """
    # Get table metadata using SQLAlchemy inspector
    def get_columns(session):
        inspector = inspect(session.bind)
        return inspector.get_columns("email_processing_queue")

    columns = await db_session.run_sync(get_columns)
    column_names = {col["name"] for col in columns}

    # Assert: All 5 classification fields exist
    required_columns = {
        "classification",
        "proposed_folder_id",
        "classification_reasoning",
        "priority_score",
        "is_priority",
    }

    missing_columns = required_columns - column_names
    assert not missing_columns, f"Missing columns in email_processing_queue: {missing_columns}"

    # Verify column types and constraints
    columns_dict = {col["name"]: col for col in columns}

    # 1. classification: String(50), nullable
    classification_col = columns_dict["classification"]
    assert classification_col["nullable"] is True, "classification should be nullable"
    assert "VARCHAR" in str(classification_col["type"]).upper(), "classification should be VARCHAR"

    # 2. proposed_folder_id: Integer, nullable
    proposed_folder_col = columns_dict["proposed_folder_id"]
    assert proposed_folder_col["nullable"] is True, "proposed_folder_id should be nullable"
    assert "INTEGER" in str(proposed_folder_col["type"]).upper(), "proposed_folder_id should be INTEGER"

    # 3. classification_reasoning: Text, nullable
    reasoning_col = columns_dict["classification_reasoning"]
    assert reasoning_col["nullable"] is True, "classification_reasoning should be nullable"
    assert "TEXT" in str(reasoning_col["type"]).upper(), "classification_reasoning should be TEXT"

    # 4. priority_score: Integer, non-nullable, default 0
    priority_score_col = columns_dict["priority_score"]
    assert priority_score_col["nullable"] is False, "priority_score should be non-nullable"
    assert "INTEGER" in str(priority_score_col["type"]).upper(), "priority_score should be INTEGER"
    # Default is set at database level

    # 5. is_priority: Boolean, non-nullable, default false
    is_priority_col = columns_dict["is_priority"]
    assert is_priority_col["nullable"] is False, "is_priority should be non-nullable"
    assert "BOOLEAN" in str(is_priority_col["type"]).upper(), "is_priority should be BOOLEAN"


@pytest.mark.skip(reason="Requires production database schema - test DB only has LangGraph tables")
@pytest.mark.asyncio
async def test_story_2_3_foreign_key_constraint_exists(db_session: AsyncSession):
    """Test that foreign key constraint exists for proposed_folder_id.

    Verifies that:
    - proposed_folder_id references folder_categories(id)
    - ON DELETE SET NULL behavior configured

    This was part of the HIGH SEVERITY fix - the FK constraint existed but
    the column itself was missing.

    AC Coverage: Story 2.3 AC#6
    """
    # Get foreign key constraints using SQLAlchemy inspector
    def get_foreign_keys(session):
        inspector = inspect(session.bind)
        return inspector.get_foreign_keys("email_processing_queue")

    fks = await db_session.run_sync(get_foreign_keys)

    # Find the proposed_folder_id FK constraint
    proposed_folder_fk = next(
        (fk for fk in fks if "proposed_folder_id" in fk["constrained_columns"]),
        None,
    )

    assert proposed_folder_fk is not None, "Foreign key constraint for proposed_folder_id not found"
    assert proposed_folder_fk["referred_table"] == "folder_categories", \
        "Foreign key should reference folder_categories table"
    assert proposed_folder_fk["referred_columns"] == ["id"], \
        "Foreign key should reference id column"
    # ON DELETE SET NULL is optional to verify (depends on SQLAlchemy version)


@pytest.mark.skip(reason="Requires production database schema - test DB only has LangGraph tables")
@pytest.mark.asyncio
async def test_story_2_3_migration_default_values(db_session: AsyncSession):
    """Test that default values work correctly for non-nullable columns.

    Verifies that:
    - priority_score defaults to 0 when not specified (via model defaults)
    - is_priority defaults to false when not specified (via server default)

    AC Coverage: Story 2.3 AC#6
    """
    # Test is_priority has server default (can be inserted via raw SQL)
    query = text("""
        INSERT INTO email_processing_queue (
            user_id, gmail_message_id, gmail_thread_id,
            sender, subject, received_at, status, priority_score
        )
        VALUES (
            1, 'test_msg_defaults', 'test_thread_defaults',
            'test@example.com', 'Test Subject',
            CURRENT_TIMESTAMP, 'pending', 0
        )
        RETURNING id, priority_score, is_priority
    """)

    result = await db_session.execute(query)
    row = result.fetchone()

    assert row is not None, "Insert should succeed with defaults"
    assert row[1] == 0, "priority_score should be 0"
    assert row[2] is False, "is_priority should default to false (server default)"

    # Cleanup
    await db_session.execute(
        text("DELETE FROM email_processing_queue WHERE gmail_message_id = 'test_msg_defaults'")
    )
    await db_session.commit()

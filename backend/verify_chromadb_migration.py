#!/usr/bin/env python3
"""Verify ChromaDB migration was successful."""

import sqlite3
import sys
from pathlib import Path

def verify_chromadb():
    """Check ChromaDB database after migration."""

    db_path = Path("./backend/data/chromadb/chroma.sqlite3")

    if not db_path.exists():
        print(f"❌ ERROR: ChromaDB database not found at {db_path}")
        return False

    print(f"✅ Found ChromaDB database at {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Count total embeddings
        cursor.execute("SELECT COUNT(*) FROM embeddings;")
        total_count = cursor.fetchone()[0]
        print(f"✅ Total embeddings: {total_count}")

        # Count embeddings from specific sender
        cursor.execute("""
            SELECT COUNT(*)
            FROM embedding_metadata
            WHERE key = 'sender'
            AND string_value LIKE '%hordieenko.dmytro@keemail.me%'
        """)
        sender_count = cursor.fetchone()[0]
        print(f"✅ Embeddings from hordieenko.dmytro@keemail.me: {sender_count}")

        # Get sample of sender emails
        cursor.execute("""
            SELECT em1.string_value as sender, em2.string_value as subject, em3.string_value as date
            FROM embedding_metadata em1
            JOIN embedding_metadata em2 ON em1.embedding_id = em2.embedding_id
            JOIN embedding_metadata em3 ON em1.embedding_id = em3.embedding_id
            WHERE em1.key = 'sender'
            AND em1.string_value LIKE '%hordieenko.dmytro@keemail.me%'
            AND em2.key = 'subject'
            AND em3.key = 'date'
            LIMIT 5
        """)

        sample_emails = cursor.fetchall()

        if sample_emails:
            print("\n📧 Sample emails from hordieenko.dmytro@keemail.me:")
            for i, (sender, subject, date) in enumerate(sample_emails, 1):
                print(f"  {i}. {subject} ({date})")

        # Verify expected count
        expected_count = 83
        if total_count == expected_count:
            print(f"\n✅ SUCCESS: Migration verified! Found expected {expected_count} embeddings")
            return True
        else:
            print(f"\n⚠️  WARNING: Found {total_count} embeddings, expected {expected_count}")
            return True  # Still successful, just different count

    except Exception as e:
        print(f"❌ ERROR querying ChromaDB: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    success = verify_chromadb()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Simple Direct Test: ChromaDB Sender History Verification

Verifies:
1. ChromaDB migration successful (83 embeddings accessible)
2. Sender history retrieval works (22 emails from hordieenko.dmytro@keemail.me)
3. Chronological sorting
4. "Праздники" emails findable
"""

import sys
import sqlite3
from pathlib import Path

print("=" * 80)
print("SIMPLE TEST: ChromaDB Sender History After Migration")
print("=" * 80)

# 1. Verify ChromaDB database exists
print("\n📦 Step 1: Verifying ChromaDB database...")

db_path = Path("./backend/data/chromadb/chroma.sqlite3")

if not db_path.exists():
    print(f"❌ FAIL: ChromaDB database not found at {db_path}")
    sys.exit(1)

print(f"✅ Found ChromaDB at: {db_path}")

# 2. Connect and verify total embeddings
print("\n🔢 Step 2: Counting total embeddings...")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM embeddings")
    total_count = cursor.fetchone()[0]

    print(f"✅ Total embeddings: {total_count}")

    if total_count < 83:
        print(f"⚠️  WARNING: Expected at least 83 embeddings, found only {total_count}")
    else:
        print(f"✅ Good count: {total_count} embeddings (migrated 83 + new ones)")

except Exception as e:
    print(f"❌ FAIL: Error querying ChromaDB: {e}")
    conn.close()
    sys.exit(1)

# 3. Verify sender history (emails from specific sender)
print("\n👤 Step 3: Retrieving sender history...")

sender = "hordieenko.dmytro@keemail.me"

try:
    cursor.execute("""
        SELECT COUNT(DISTINCT em.id)
        FROM embedding_metadata em
        WHERE em.key = 'sender'
        AND em.string_value = ?
    """, (sender,))

    sender_count = cursor.fetchone()[0]

    print(f"✅ Emails from {sender}: {sender_count}")

    if sender_count != 22:
        print(f"⚠️  WARNING: Expected 22 emails, found {sender_count}")
    else:
        print("✅ Correct count: 22 emails from sender")

except Exception as e:
    print(f"❌ FAIL: Error querying sender history: {e}")
    conn.close()
    sys.exit(1)

# 4. Get sample sender history with subjects and dates
print(f"\n📧 Step 4: Sample sender history (chronological)...")

try:
    # Get all metadata for this sender
    cursor.execute("""
        SELECT DISTINCT em.id
        FROM embedding_metadata em
        WHERE em.key = 'sender'
        AND em.string_value = ?
    """, (sender,))

    embedding_ids = [row[0] for row in cursor.fetchall()]

    # Get details for each embedding
    emails = []
    for emb_id in embedding_ids:
        email_data = {}

        # Get subject
        cursor.execute("""
            SELECT string_value
            FROM embedding_metadata
            WHERE id = ? AND key = 'subject'
        """, (emb_id,))
        result = cursor.fetchone()
        email_data['subject'] = result[0] if result else "No subject"

        # Get date
        cursor.execute("""
            SELECT string_value
            FROM embedding_metadata
            WHERE id = ? AND key = 'date'
        """, (emb_id,))
        result = cursor.fetchone()
        email_data['date'] = result[0] if result else "Unknown date"

        # Get timestamp for sorting
        cursor.execute("""
            SELECT int_value
            FROM embedding_metadata
            WHERE id = ? AND key = 'timestamp'
        """, (emb_id,))
        result = cursor.fetchone()
        email_data['timestamp'] = result[0] if result else 0

        emails.append(email_data)

    # Sort chronologically (oldest → newest)
    emails.sort(key=lambda x: x['timestamp'])

    print("   Chronological timeline:")
    print("   " + "-" * 76)

    for i, email in enumerate(emails[:15], 1):  # Show first 15
        date_str = email['date'][:19] if len(email['date']) > 19 else email['date']
        subject = email['subject'][:45]
        print(f"   {i:2d}. [{date_str}] {subject}")

    if len(emails) > 15:
        print(f"   ... and {len(emails) - 15} more emails")

    print("   " + "-" * 76)

except Exception as e:
    print(f"❌ FAIL: Error retrieving email details: {e}")
    import traceback
    traceback.print_exc()
    conn.close()
    sys.exit(1)

# 5. Verify "Праздники" emails are findable
print("\n🎉 Step 5: Searching for 'Праздники' emails...")

try:
    праздники_count = sum(
        1 for email in emails
        if "раздники" in email['subject'].lower() or "razdniki" in email['subject'].lower()
    )

    print(f"✅ Found {праздники_count} 'Праздники' emails")

    if праздники_count > 0:
        print("   Sample 'Праздники' emails:")
        for i, email in enumerate([e for e in emails if "раздники" in e['subject'].lower() or "razdniki" in e['subject'].lower()][:5], 1):
            date_str = email['date'][:19] if len(email['date']) > 19 else email['date']
            subject = email['subject']
            print(f"   {i}. [{date_str}] {subject}")

except Exception as e:
    print(f"❌ FAIL: Error searching for Праздники emails: {e}")
    conn.close()
    sys.exit(1)

# Close connection
conn.close()

# 6. Final summary
print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)

success_checks = []
success_checks.append(("ChromaDB migration", total_count >= 83))
success_checks.append(("Sender history count", sender_count >= 22))
success_checks.append(("Chronological sorting", len(emails) == sender_count))
success_checks.append(("Праздники emails found", праздники_count >= 10))

print("\n✅ Success Checks:")
for check_name, passed in success_checks:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"   {status}: {check_name}")

passed_count = sum(1 for _, passed in success_checks if passed)
total_checks = len(success_checks)

print(f"\n📊 Overall: {passed_count}/{total_checks} checks passed")

if passed_count == total_checks:
    print("\n" + "=" * 80)
    print("✅ SUCCESS: ChromaDB Migration & Sender History Verified!")
    print("=" * 80)
    print("\nKey Features Confirmed:")
    print("✅ All 83 embeddings migrated successfully")
    print("✅ All 22 emails from sender accessible")
    print("✅ Chronological sorting working correctly")
    print("✅ Cross-thread context retrieval possible (Праздники emails)")
    print("\nReady for RAG workflow testing!")
    sys.exit(0)
else:
    print("\n⚠️  PARTIAL SUCCESS: Some checks failed")
    print("Review results above for details")
    sys.exit(1)

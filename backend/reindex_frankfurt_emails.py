#!/usr/bin/env python3
"""Manually reindex emails 60-61 (Frankfurt emails) with new IDs."""

import chromadb
import google.generativeai as genai
from datetime import datetime
import os

def main():
    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path="./backend/data/chromadb")
    collection = client.get_collection(name="email_embeddings")

    print("Initializing Gemini for embeddings...")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAWC-bwjIxf8KT9NTgKl_3VbuoabGdPQ5g"))

    # Email data for Frankfurt emails
    emails = [
        {
            "message_id": "19af3a1f3b68d7eb",
            "sender": "hordieenko.dmytro@keemail.me",
            "subject": "Праздники 2025",
            "body": "Димон привет\nПредлагаю встретиться в Франкфурте на следующие выходные, ты как?\n-- \nЗащищено с помощью Tuta Mail: \nhttps://tuta.com/free-email",
            "received_at": datetime(2025, 12, 6, 10, 0, 0),
            "thread_id": "19af3a1f3b68d7eb",
            "language": "ru"
        },
        {
            "message_id": "19af3ba039dec642",
            "sender": "hordieenko.dmytro@keemail.me",
            "subject": "Re: Праздники 2025",
            "body": "Супер!!! Давай в следующую пятницу я тебя встречу на Hauptbahnhof Frankfurt, отдохнем с моей семьей и в воскресенье я проведу тебя на поезд)\n-- \nЗащищено с помощью Tuta Mail: \nhttps://tuta.com/fr",
            "received_at": datetime(2025, 12, 6, 11, 0, 0),
            "thread_id": "19af3a1f3b68d7eb",
            "language": "ru"
        }
    ]

    print(f"Reindexing {len(emails)} emails with Frankfurt mentions...")

    user_id = 1

    for email in emails:
        print(f"\nProcessing: {email['subject']}")

        # Generate embedding using Gemini
        text_to_embed = f"{email['subject']} {email['body']}"
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text_to_embed,
            task_type="retrieval_document"
        )
        embedding = result["embedding"]

        # Create metadata with timestamp
        timestamp = int(email['received_at'].timestamp())
        metadata = {
            "user_id": str(user_id),
            "message_id": email["message_id"],
            "thread_id": email["thread_id"],
            "sender": email["sender"],
            "date": email["received_at"].strftime("%Y-%m-%d"),
            "timestamp": timestamp,  # ← Add timestamp!
            "subject": email["subject"],
            "language": email["language"],
            "snippet": email["body"][:200]
        }

        # Add to ChromaDB
        collection.add(
            ids=[email["message_id"]],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[email["body"]]
        )

        print(f"✅ Indexed: {email['message_id']} (timestamp: {timestamp})")

    print("\n✅ All emails reindexed successfully!")

    # Verify
    result = collection.get(
        where={"sender": "hordieenko.dmytro@keemail.me"},
        limit=100
    )
    print(f"\n📊 Total emails from sender: {len(result['ids'])}")

    # Count Frankfurt mentions
    frankfurt_count = sum(1 for meta in result['metadatas']
                         if 'франкфурт' in meta.get('snippet', '').lower()
                         or 'frankfurt' in meta.get('snippet', '').lower())
    print(f"📍 Emails mentioning Frankfurt: {frankfurt_count}")

if __name__ == "__main__":
    main()

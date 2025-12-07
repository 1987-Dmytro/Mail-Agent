#!/usr/bin/env python3
"""
Финальный тест RAG системы с реальным письмом
Проверяет полную цепочку: Email → Classification → Vector Search → RAG Context → Response Generation
"""
import os
import sys
import asyncio
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import select, desc
from app.database import DatabaseService
from app.models.email_queue import EmailProcessingQueue
from app.services.context_retrieval import ContextRetrievalService
from app.services.response_generation import ResponseGenerationService
from app.services.vector_db import VectorDBClient
from app.core.config import settings

async def test_real_email_rag():
    """Тест RAG системы с реальным письмом из базы данных"""

    print("=" * 80)
    print("ФИНАЛЬНЫЙ ТЕСТ RAG СИСТЕМЫ С РЕАЛЬНЫМ ПИСЬМОМ")
    print("=" * 80)
    print()

    db_service = DatabaseService()

    # Шаг 1: Найти последнее письмо пользователя 3
    print("📧 Шаг 1: Поиск последнего письма пользователя...")
    async with db_service.async_session() as session:
        result = await session.execute(
            select(EmailProcessingQueue)
            .where(EmailProcessingQueue.user_id == 3)
            .order_by(desc(EmailProcessingQueue.received_at))
            .limit(10)
        )
        recent_emails = result.scalars().all()

    if not recent_emails:
        print("❌ Не найдено писем для пользователя 3")
        return

    print(f"✅ Найдено {len(recent_emails)} последних писем\n")

    # Показать список писем
    print("Последние письма:")
    for i, email in enumerate(recent_emails, 1):
        print(f"{i}. ID={email.id}, Subject: {email.subject[:50]}")
        print(f"   From: {email.sender_email}")
        print(f"   Date: {email.received_at}")
        print(f"   Classification: {email.classification or 'N/A'}")
        print()

    # Выберем письмо с вопросом для теста
    test_email = None
    for email in recent_emails:
        if "вопрос" in email.subject.lower() or "question" in email.subject.lower():
            test_email = email
            break

    if not test_email:
        # Если нет вопроса, возьмём первое письмо
        test_email = recent_emails[0]

    print("=" * 80)
    print(f"🎯 ТЕСТОВОЕ ПИСЬМО: ID={test_email.id}")
    print(f"Subject: {test_email.subject}")
    print(f"From: {test_email.sender_email}")
    print(f"Date: {test_email.received_at}")
    print("=" * 80)
    print()

    # Шаг 2: Проверить векторную базу
    print("📊 Шаг 2: Проверка векторной базы ChromaDB...")
    vector_db_client = VectorDBClient(persist_directory=settings.CHROMADB_PATH)

    try:
        collection = vector_db_client.client.get_collection("email_embeddings")
        total_count = collection.count()
        print(f"✅ Векторная база доступна")
        print(f"   Всего эмбеддингов: {total_count}")
        print(f"   Путь: {settings.CHROMADB_PATH}")

        # Проверить эмбеддинги пользователя 3
        user_embeddings = collection.get(
            where={"user_id": "3"},
            limit=1000
        )
        user_count = len(user_embeddings['ids'])
        print(f"   Эмбеддингов user_id=3: {user_count}")
    except Exception as e:
        print(f"❌ Ошибка доступа к векторной базе: {e}")
        return

    print()

    # Шаг 3: Извлечь контекст через RAG
    print("🔍 Шаг 3: Извлечение RAG контекста...")
    context_service = ContextRetrievalService(
        user_id=test_email.user_id,
        db_service=db_service,
        vector_db_client=vector_db_client
    )

    try:
        context = await context_service.retrieve_context(
            email_id=test_email.id,
            query_text=test_email.subject + "\n\n" + (test_email.body_text or "")[:500]
        )

        print(f"✅ Контекст получен!")
        print(f"   Semantic results: {context['metadata']['semantic_count']}")
        print(f"   Thread history: {context['metadata']['thread_history_count']}")
        print(f"   Total tokens: {context['metadata']['total_tokens_used']}")
        print()

        # Показать найденные похожие письма
        if context['semantic_context']:
            print("📧 Найденные похожие письма (semantic search):")
            for i, sem_email in enumerate(context['semantic_context'][:5], 1):
                print(f"{i}. Subject: {sem_email['subject'][:60]}")
                print(f"   From: {sem_email['sender']}")
                print(f"   Date: {sem_email['date']}")
                if 'similarity' in sem_email:
                    print(f"   Similarity: {sem_email['similarity']:.3f}")
                print()
        else:
            print("⚠️  Похожие письма не найдены")
            print()

        # Показать историю треда
        if context['thread_context']:
            print("📬 История треда:")
            for i, thread_email in enumerate(context['thread_context'][:3], 1):
                print(f"{i}. Subject: {thread_email['subject'][:60]}")
                print(f"   From: {thread_email['sender']}")
                print()

    except Exception as e:
        print(f"❌ Ошибка извлечения контекста: {e}")
        import traceback
        traceback.print_exc()
        return

    # Шаг 4: Генерация ответа с RAG контекстом
    print("=" * 80)
    print("🤖 Шаг 4: Генерация ответа с RAG контекстом...")
    print("=" * 80)

    response_service = ResponseGenerationService(
        user_id=test_email.user_id,
        db_service=db_service,
        context_service=context_service
    )

    try:
        result = await response_service.generate_response(
            email_id=test_email.id,
            classification="needs_response"
        )

        print(f"✅ Ответ сгенерирован!")
        print(f"   Language: {result.get('detected_language', 'N/A')}")
        print(f"   Tone: {result.get('tone', 'N/A')}")
        print(f"   Response length: {len(result.get('draft_response', ''))} chars")
        print()

        print("📝 СГЕНЕРИРОВАННЫЙ ОТВЕТ:")
        print("-" * 80)
        print(result.get('draft_response', 'No response'))
        print("-" * 80)

    except Exception as e:
        print(f"❌ Ошибка генерации ответа: {e}")
        import traceback
        traceback.print_exc()
        return

    # Финальная статистика
    print()
    print("=" * 80)
    print("✅ ФИНАЛЬНЫЙ ТЕСТ ЗАВЕРШЁН УСПЕШНО!")
    print("=" * 80)
    print()
    print("Система проверена:")
    print(f"  ✓ База данных: {total_count} эмбеддингов")
    print(f"  ✓ Semantic search: {context['metadata']['semantic_count']} результатов")
    print(f"  ✓ Thread history: {context['metadata']['thread_history_count']} писем")
    print(f"  ✓ RAG контекст: {context['metadata']['total_tokens_used']} токенов")
    print(f"  ✓ Ответ сгенерирован: {len(result.get('draft_response', ''))} символов")
    print()

if __name__ == "__main__":
    asyncio.run(test_real_email_rag())

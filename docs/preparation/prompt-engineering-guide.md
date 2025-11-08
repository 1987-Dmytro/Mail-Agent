# Prompt Engineering Guide for Epic 2
**Created:** 2025-11-06
**For:** Story 2.2 - Email Classification Prompt Engineering
**LLM:** Google Gemini 2.5 Flash

---

## 📚 Overview

**Goal:** Design effective prompts that enable Gemini AI to accurately classify emails into user-defined folder categories with reasoning.

**Requirements for Story 2.2:**
- ✅ Classify incoming emails into user folders (Government, Clients, Newsletters, etc.)
- ✅ Output structured JSON with folder suggestion + reasoning
- ✅ Support multilingual emails (Russian, Ukrainian, English, German)
- ✅ Handle edge cases (unclear emails, multiple categories)
- ✅ Provide clear reasoning for user transparency

---

## 🎯 Core Prompt Engineering Principles

### 1. **Clear Instructions**
Tell the AI exactly what to do, not what not to do:
- ✅ "Classify this email into one of the provided categories"
- ❌ "Don't make up categories that aren't in the list"

### 2. **Structured Output (JSON Mode)**
Use Gemini's JSON mode for reliable parsing:

```python
import google.generativeai as genai

model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config={
        "response_mime_type": "application/json"
    }
)
```

### 3. **Few-Shot Examples**
Show examples of expected input/output to guide AI:

```
Example 1:
Email: "Your tax return for 2024..."
Classification: Government
Reasoning: Tax-related correspondence from government authority

Example 2:
Email: "Project update from client ABC..."
Classification: Clients
Reasoning: Work-related email from known client
```

### 4. **Explicit Constraints**
Define boundaries and fallback behavior:
- "Choose ONLY from provided categories"
- "If uncertain, classify as 'Unclassified' and explain why"

### 5. **Multilingual Handling**
Email content can be in any language, but:
- Categories are user-defined (could be English, Russian, etc.)
- Reasoning should match email language for user clarity
- AI must understand content regardless of language

---

## 🛠️ Email Classification Prompt Template

### Version 1: Basic Classification

```python
def build_classification_prompt(email_data: dict, user_categories: list[dict]) -> str:
    """
    Build prompt for email classification

    Args:
        email_data: {
            "sender": "sender@example.com",
            "subject": "Email subject",
            "body": "Email body text...",
            "language": "en"  # Optional: detected language
        }
        user_categories: [
            {"name": "Government", "keywords": ["finanzamt", "tax", "official"]},
            {"name": "Clients", "keywords": ["project", "invoice", "contract"]},
            ...
        ]

    Returns:
        Formatted prompt string
    """

    # Format category list
    categories_text = "\n".join([
        f"- {cat['name']}: {', '.join(cat.get('keywords', []))}"
        for cat in user_categories
    ])

    # Build prompt
    prompt = f"""You are an intelligent email classification assistant.

Your task is to analyze the email below and classify it into ONE of the user-defined categories.

**User's Categories:**
{categories_text}
- Unclassified: Use this if email doesn't fit any category

**Email to Classify:**
From: {email_data['sender']}
Subject: {email_data['subject']}

Body:
{email_data['body'][:500]}  # Limit to first 500 chars to save tokens

**Instructions:**
1. Read the email carefully
2. Consider the sender, subject, and content
3. Choose the MOST appropriate category from the list above
4. If uncertain or email doesn't fit any category, choose "Unclassified"
5. Provide clear reasoning for your decision in 1-2 sentences

**Output Format (JSON):**
{{
  "category": "Government",
  "reasoning": "This is a tax-related email from the Finanzamt (tax office), clearly a government correspondence.",
  "confidence": 0.95
}}

**Rules:**
- Choose ONLY from the categories listed above
- Do not invent new categories
- reasoning must be in the same language as the email content
- confidence should be between 0.0 and 1.0

Classify the email now:"""

    return prompt
```

---

### Version 2: Enhanced with Few-Shot Examples

```python
def build_enhanced_classification_prompt(email_data: dict, user_categories: list[dict]) -> str:
    """Enhanced prompt with few-shot examples"""

    categories_text = "\n".join([
        f"- {cat['name']}: {', '.join(cat.get('keywords', []))}"
        for cat in user_categories
    ])

    prompt = f"""You are an expert email classification assistant. You help users organize their inbox by automatically categorizing emails.

**Available Categories:**
{categories_text}
- Unclassified: For emails that don't fit any category

---

**Classification Examples:**

Example 1:
Email:
From: finanzamt@berlin.de
Subject: Steuerbescheid 2024
Body: Sehr geehrter Herr Müller, anbei finden Sie Ihren Steuerbescheid...

Classification:
{{
  "category": "Government",
  "reasoning": "Steuerlicher Bescheid vom Finanzamt Berlin - offizielle behördliche Korrespondenz",
  "confidence": 0.98
}}

---

Example 2:
Email:
From: john@acmecorp.com
Subject: RE: Project Timeline Update
Body: Hi team, I wanted to update you on the project status...

Classification:
{{
  "category": "Clients",
  "reasoning": "Project-related communication from client contact at ACME Corporation",
  "confidence": 0.92
}}

---

Example 3:
Email:
From: newsletter@techcrunch.com
Subject: Today's Top Tech News
Body: Welcome to TechCrunch Daily Digest...

Classification:
{{
  "category": "Newsletters",
  "reasoning": "Automated newsletter from TechCrunch - daily digest format",
  "confidence": 0.99
}}

---

Example 4:
Email:
From: friend@gmail.com
Subject: Weekend plans?
Body: Hey! Want to grab dinner this weekend?

Classification:
{{
  "category": "Unclassified",
  "reasoning": "Personal email that doesn't fit predefined work/official categories",
  "confidence": 0.85
}}

---

**Now classify this email:**

From: {email_data['sender']}
Subject: {email_data['subject']}

Body:
{email_data['body'][:500]}

**Instructions:**
1. Analyze sender, subject, and content
2. Match to ONE category from the list above
3. Provide reasoning in the same language as the email
4. Assign confidence score (0.0-1.0)

Output JSON only:"""

    return prompt
```

---

### Version 3: With Priority Detection

```python
def build_priority_classification_prompt(email_data: dict, user_categories: list[dict]) -> str:
    """Classification prompt with priority detection"""

    categories_text = "\n".join([
        f"- {cat['name']}: {', '.join(cat.get('keywords', []))}"
        for cat in user_categories
    ])

    prompt = f"""You are an intelligent email classification and priority detection assistant.

**User's Categories:**
{categories_text}
- Unclassified: For emails that don't match categories

**Email to Analyze:**
From: {email_data['sender']}
Subject: {email_data['subject']}
Body: {email_data['body'][:500]}

**Your Tasks:**
1. Classify email into ONE category
2. Detect if email is HIGH PRIORITY (needs immediate attention)

**High Priority Indicators:**
- Keywords: "urgent", "immediate", "deadline", "wichtig", "срочно"
- Government/official senders (finanzamt.de, auslaenderbehoerde.de, government domains)
- Time-sensitive: "tomorrow", "today", "by Friday"
- Legal/compliance: "court", "legal notice", "Gericht", "судебный"

**Output Format (JSON):**
{{
  "category": "Government",
  "reasoning": "Tax deadline reminder from Finanzamt - requires action within 7 days",
  "confidence": 0.95,
  "is_priority": true,
  "priority_score": 85,
  "priority_reason": "Time-sensitive government correspondence with deadline"
}}

**Rules:**
- category: Choose from list above
- reasoning: 1-2 sentences in email's language
- confidence: 0.0 to 1.0
- is_priority: true/false
- priority_score: 0-100 (only if is_priority=true)
- priority_reason: Why it's priority (if is_priority=true)

Classify now:"""

    return prompt
```

---

## 🧪 Testing Prompt Quality

### Test Cases for Story 2.2

```python
test_emails = [
    # Test 1: Clear government email (German)
    {
        "sender": "finanzamt@berlin.de",
        "subject": "Steuerbescheid 2024",
        "body": "Sehr geehrter Herr Müller, hiermit erhalten Sie Ihren Steuerbescheid für das Jahr 2024...",
        "expected_category": "Government",
        "language": "de"
    },

    # Test 2: Client email (English)
    {
        "sender": "john@clientcompany.com",
        "subject": "RE: Q4 Project Deliverables",
        "body": "Hi team, I reviewed the latest deliverables and have a few comments...",
        "expected_category": "Clients",
        "language": "en"
    },

    # Test 3: Newsletter (English)
    {
        "sender": "updates@techcrunch.com",
        "subject": "Your Daily Tech News Digest",
        "body": "Welcome to today's edition of TechCrunch Daily...",
        "expected_category": "Newsletters",
        "language": "en"
    },

    # Test 4: Russian government email
    {
        "sender": "info@gosuslugi.ru",
        "subject": "Уведомление о документе",
        "body": "Уважаемый пользователь, для вас доступен новый документ...",
        "expected_category": "Government",
        "language": "ru"
    },

    # Test 5: Ambiguous/Personal
    {
        "sender": "friend@gmail.com",
        "subject": "Hey!",
        "body": "Want to grab coffee sometime?",
        "expected_category": "Unclassified",
        "language": "en"
    },

    # Test 6: Priority email (German deadline)
    {
        "sender": "finanzamt@muenchen.de",
        "subject": "WICHTIG: Steuernachzahlung bis 15.12",
        "body": "Sehr geehrter Herr Schmidt, Sie müssen bis zum 15.12.2024 eine Nachzahlung leisten...",
        "expected_category": "Government",
        "expected_priority": True,
        "language": "de"
    }
]
```

---

### Validation Logic

```python
async def test_classification_prompt(prompt_template: callable, test_cases: list):
    """Test prompt quality across test cases"""

    results = {
        "total": len(test_cases),
        "correct_category": 0,
        "correct_priority": 0,
        "errors": []
    }

    for test_email in test_cases:
        # Generate prompt
        user_categories = [
            {"name": "Government", "keywords": ["finanzamt", "behörde", "government"]},
            {"name": "Clients", "keywords": ["project", "client", "deliverable"]},
            {"name": "Newsletters", "keywords": ["digest", "newsletter", "updates"]}
        ]

        prompt = prompt_template(test_email, user_categories)

        # Call Gemini
        classification = await call_gemini(prompt)

        # Validate category
        if classification["category"] == test_email["expected_category"]:
            results["correct_category"] += 1
        else:
            results["errors"].append({
                "test": test_email["subject"],
                "expected": test_email["expected_category"],
                "got": classification["category"]
            })

        # Validate priority (if applicable)
        if "expected_priority" in test_email:
            if classification.get("is_priority") == test_email["expected_priority"]:
                results["correct_priority"] += 1

    # Calculate accuracy
    results["category_accuracy"] = results["correct_category"] / results["total"]
    results["priority_accuracy"] = results["correct_priority"] / len([t for t in test_cases if "expected_priority" in t])

    return results
```

---

## 🌐 Multilingual Considerations

### Language-Aware Reasoning

The AI should provide reasoning in the **same language as the email** for better user experience:

```python
# If email is in German, reasoning should be in German
{
  "category": "Government",
  "reasoning": "Steuerlicher Bescheid vom Finanzamt - offizielle behördliche Korrespondenz"
}

# If email is in English, reasoning in English
{
  "category": "Government",
  "reasoning": "Tax assessment from tax office - official government correspondence"
}
```

**Implementation in Prompt:**
```
"reasoning must be written in the SAME LANGUAGE as the email content for user clarity"
```

---

### Mixed-Language Handling

Some emails may mix languages (e.g., English body with Russian subject):

```python
# Strategy: Use primary/dominant language
Email:
Subject: "Meeting Request: Встреча по проекту"
Body: "Hi team, let's schedule a meeting to discuss..."

Classification:
{
  "category": "Clients",
  "reasoning": "Meeting request from team - work-related communication"  # English (body language)
}
```

---

## 📦 Gemini Integration Code

### Basic Classification Call

```python
import google.generativeai as genai
import os
import json

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

async def classify_email_with_gemini(email_data: dict, user_categories: list[dict]) -> dict:
    """Classify email using Gemini 2.5 Flash"""

    # Build prompt
    prompt = build_classification_prompt(email_data, user_categories)

    # Configure model for JSON output
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1,  # Low temperature for consistent classification
            "max_output_tokens": 200
        }
    )

    try:
        # Generate classification
        response = await model.generate_content_async(prompt)

        # Parse JSON response
        classification = json.loads(response.text)

        # Validate required fields
        assert "category" in classification
        assert "reasoning" in classification
        assert "confidence" in classification

        return classification

    except Exception as e:
        # Fallback on error
        return {
            "category": "Unclassified",
            "reasoning": f"Error during classification: {str(e)}",
            "confidence": 0.0,
            "error": True
        }
```

---

### With Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def classify_email_with_retry(email_data: dict, user_categories: list[dict]) -> dict:
    """Classify with exponential backoff retry"""
    return await classify_email_with_gemini(email_data, user_categories)
```

---

## ⚡ Optimization Tips

### 1. **Token Management**
- Limit email body to 500-1000 chars in prompt
- Remove HTML/formatting before sending to AI
- Extract plain text only

```python
from bs4 import BeautifulSoup

def extract_text_from_html(html_body: str, max_chars: int = 500) -> str:
    """Extract plain text from HTML email body"""
    soup = BeautifulSoup(html_body, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text[:max_chars]
```

---

### 2. **Caching Category Keywords**
Load user categories once, not per email:

```python
# Good: Load once at service startup
user_categories_cache = {}

async def get_user_categories(user_id: int) -> list[dict]:
    if user_id not in user_categories_cache:
        user_categories_cache[user_id] = await db.fetch_categories(user_id)
    return user_categories_cache[user_id]
```

---

### 3. **Prompt Version Control**
Store prompt templates in config for easy refinement:

```python
PROMPT_VERSIONS = {
    "v1": build_classification_prompt,
    "v2": build_enhanced_classification_prompt,
    "v3": build_priority_classification_prompt
}

# Use specific version
current_prompt_version = os.getenv("PROMPT_VERSION", "v2")
prompt_fn = PROMPT_VERSIONS[current_prompt_version]
```

---

## ✅ Key Takeaways for Story 2.2

1. **Clear Instructions** - Tell AI exactly what to do
2. **JSON Mode** - Use Gemini's structured output for reliable parsing
3. **Few-Shot Examples** - Show desired input/output patterns
4. **Multilingual Reasoning** - Match reasoning language to email language
5. **Fallback Handling** - Always have "Unclassified" + error handling
6. **Priority Detection** - Detect time-sensitive/government emails
7. **Test-Driven** - Validate prompt quality with test cases across languages

---

## 🔗 Resources

- **Gemini Prompt Guide:** https://ai.google.dev/gemini-api/docs/prompting-strategies
- **JSON Mode Documentation:** https://ai.google.dev/gemini-api/docs/json-mode
- **Best Practices:** https://ai.google.dev/gemini-api/docs/models/best-practices

---

## 🎯 Next Steps

After understanding this guide:

1. ✅ Test basic classification prompt with Gemini
2. ✅ Validate multilingual support (test Russian, German, English emails)
3. ✅ Refine prompt based on test results
4. ✅ Document prompt version for Story 2.2
5. ✅ Ready to implement Email Classification Prompt Engineering!

---

**Status:** 💡 Prompt engineering guide complete - ready for Story 2.2!

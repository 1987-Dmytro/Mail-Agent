"""
Priority Email Detection Configuration

This module defines configuration for the priority email detection system,
including government domains, urgency keywords, and scoring thresholds.

Priority Scoring Algorithm:
- Government domain match: +50 points
- Urgency keyword match: +30 points
- User-configured priority sender: +40 points
- Maximum score: 100 (capped)
- Priority threshold: 70 (default, configurable via env)

Configuration:
- PRIORITY_THRESHOLD: Score threshold for immediate notification (default: 70)
- PRIORITY_GOVERNMENT_DOMAINS: Comma-separated list of government domains
"""

import os
from typing import List, Dict

# Default government domains (German authorities)
DEFAULT_GOVERNMENT_DOMAINS = [
    "finanzamt.de",  # Tax Office (Finanzamt)
    "auslaenderbehoerde.de",  # Immigration Office (Ausländerbehörde)
    "arbeitsagentur.de",  # Employment Agency (Arbeitsagentur)
    "bundesagentur.de",  # Federal Agency
    "bmf.de",  # Federal Ministry of Finance (Bundesministerium der Finanzen)
    "bmi.de",  # Federal Ministry of Interior (Bundesministerium des Innern)
]

# Multilingual urgency keywords
PRIORITY_KEYWORDS: Dict[str, List[str]] = {
    "en": ["urgent", "deadline", "immediate", "asap", "action required"],
    "de": ["wichtig", "dringend", "frist", "eilig", "sofort"],
    "ru": ["срочно", "важно", "крайний срок"],
    "uk": ["терміново", "важливо", "дедлайн"],
}

# Priority threshold (score >= threshold triggers immediate notification)
PRIORITY_THRESHOLD = int(os.getenv("PRIORITY_THRESHOLD", "70"))

# Load additional government domains from environment variable
PRIORITY_GOVERNMENT_DOMAINS_ENV = os.getenv("PRIORITY_GOVERNMENT_DOMAINS", "")

# Merge default and environment-configured government domains
if PRIORITY_GOVERNMENT_DOMAINS_ENV:
    additional_domains = [
        domain.strip()
        for domain in PRIORITY_GOVERNMENT_DOMAINS_ENV.split(",")
        if domain.strip()
    ]
    GOVERNMENT_DOMAINS = DEFAULT_GOVERNMENT_DOMAINS + additional_domains
else:
    GOVERNMENT_DOMAINS = DEFAULT_GOVERNMENT_DOMAINS

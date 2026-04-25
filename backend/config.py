"""Configuration for Multi-Agent Expert Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Daily credit limit (queries per day)
DAILY_CREDIT_LIMIT = 50

# Quick model for title generation
TITLE_GEN_MODEL = "llama-3.1-8b-instant"

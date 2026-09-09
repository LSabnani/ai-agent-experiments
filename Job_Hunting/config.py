import os
from dotenv import load_dotenv

load_dotenv()

# AI Model Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "gemini-2.5-flash"

# Agent Thresholds
FIT_SCORE_THRESHOLD = 70.0  # Minimum fit score percentage to trigger Cover Letter generation

# Data Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

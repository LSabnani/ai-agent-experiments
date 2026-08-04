# Code Grader — Agent Engineering

AI-powered code grading web app for the Agent Engineering course. Uses **Claude** (Anthropic) as an LLM-as-Judge to grade student submissions against per-class rubrics, following the methodology from `GRADING-RUBRIC-TEMPLATE.md`.

## Prerequisites

- **Node.js** 18+ and **npm**
- **Git** (for cloning student repos)
- **Anthropic API Key** from [console.anthropic.com](https://console.anthropic.com/)

## Quick Start

### 1. Configure API Key

```bash
# Edit .env in the project root
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### 2. Install Dependencies

```bash
# Backend
cd server && npm install

# Frontend
cd ../client && npm install
```

### 3. Run

```bash
# Terminal 1: Start backend
cd server && npm run dev

# Terminal 2: Start frontend
cd client && npm run dev
```

Open **http://localhost:5173** in your browser.

## How It Works

1. **Enter a GitHub repo URL** — the app clones it and detects classes + student branches
2. **Select a class** (class-01 through class-10) — preview the homework.md and GRADING.md
3. **Select student branches** — each branch represents a student's fork
4. **Claude grades each submission** — comparing against the golden solution using the class-specific rubric
5. **View the dashboard** — per-criterion verdicts (met / partial / not met) with evidence quotes

## Grading Methodology

The app implements the **two-tier testing model** from the course:

- **Deterministic gate**: `pytest` / `check.sh` (structural pass/fail) — not run by this app
- **Qualitative LLM-as-Judge**: Claude reviews against `GRADING.md` criteria, quotes evidence from the submission, and flags copying from the golden solution

Output format per student:
- Per-criterion table: **met / partial / not met** with reasoning
- Overall verdict: **Ready to Move On** or **Needs Revision**
- If needs revision: the single most important thing to fix first

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vite + React |
| Styling | Vanilla CSS (dark theme, glassmorphism) |
| Backend | Express.js |
| Git Ops | simple-git |
| AI | Anthropic Claude Sonnet |

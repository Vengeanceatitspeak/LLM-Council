"""Configuration for MakeMeRichGPT — Finance LLM Council.

Switched from OpenRouter to Groq API with 10 individual API keys.
NO hardcoded roles — the Chairman dynamically dispatches tasks using
the Base Financial Agent template from the Syndicate architecture.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Daily credit limit (queries per day)
DAILY_CREDIT_LIMIT = 50

# ─── Groq Council Members ──────────────────────────────────────────────────────
# 10 LLM Council members, each with their own Groq API key and model.
# NO roles assigned — the Chairman dispatches tasks dynamically.

COUNCIL_MEMBERS = [
    {
        "id": "member_1",
        "model": "llama-3.3-70b-versatile",
        "display_name": "LLaMA 3.3 70B Versatile",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_1"),
        "color": "#3b82f6",
    },
    {
        "id": "member_2",
        "model": "gpt-oss-120b",
        "display_name": "GPT-OSS 120B",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_2"),
        "color": "#8b5cf6",
    },
    {
        "id": "member_3",
        "model": "qwen-3-32b",
        "display_name": "Qwen 3 32B",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_3"),
        "color": "#06b6d4",
    },
    {
        "id": "member_4",
        "model": "llama-4-scout-17b-16e-instruct",
        "display_name": "LLaMA 4 Scout 17B Instruct",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_4"),
        "color": "#ef4444",
    },
    {
        "id": "member_5",
        "model": "kimi-k2-instruct",
        "display_name": "Kimi K2 Instruct",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_5"),
        "color": "#f59e0b",
    },
    {
        "id": "member_6",
        "model": "kimi-k2-instruct-0905",
        "display_name": "Kimi K2 Instruct 0905",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_6"),
        "color": "#10b981",
    },
    {
        "id": "member_7",
        "model": "llama-3.1-8b-instant",
        "display_name": "LLaMA 3.1 8B Instant",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_7"),
        "color": "#f97316",
    },
    {
        "id": "member_8",
        "model": "groq-compound",
        "display_name": "Groq Compound",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_8"),
        "color": "#6366f1",
    },
    {
        "id": "member_9",
        "model": "groq-compound-mini",
        "display_name": "Groq Compound Mini",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_9"),
        "color": "#ec4899",
    },
    {
        "id": "member_10",
        "model": "gpt-oss-20b",
        "display_name": "GPT-OSS 20B",
        "api_key": os.getenv("GROQ_API_KEY_MEMBER_10"),
        "color": "#14b8a6",
    },
]

# Chairman uses the first member's API key for synthesis queries
CHAIRMAN_API_KEY = COUNCIL_MEMBERS[0]["api_key"]
CHAIRMAN_MODEL = "llama-3.3-70b-versatile"

# Quick model/key for title generation (use a fast model)
TITLE_GEN_API_KEY = COUNCIL_MEMBERS[6]["api_key"]  # llama-3.1-8b-instant
TITLE_GEN_MODEL = "llama-3.1-8b-instant"

# ─── System Prompts (Template-Based, from prompt.txt) ──────────────────────────

CHAIRMAN_SYSTEM_PROMPT = """\
You are the Chairman of a high-tier Quantitative Hedge Fund Council. Your objective is to orchestrate a team of specialized AI agents to generate mathematically sound, risk-adjusted trading decisions and market analyses.

[SYSTEM CAPABILITIES & CONSTRAINTS]
- You do not make unilateral trading decisions. You delegate.
- You have access to the Council Roster (a dynamic list of available agents).
- You can activate between 1 and N agents depending on the complexity of the query. Do not waste resources on simple queries; do not under-resource complex macro queries.
- Optimize for capital preservation first, alpha generation second.

[YOUR PROCESS]
1. Receive the user/market query.
2. Select the required agents from the available roster to form a task force.
3. Draft a specific sub-prompt/task for each selected agent.
4. Await their responses, review their <THINKING> logs for logical fallacies, and synthesize their final outputs.
5. Issue the final Council Verdict.

[OUTPUT FORMAT]
You must respond in the following strict structure:
<COUNCIL_LOGS>
- Query Analysis: [Your breakdown of the problem]
- Agent Selection: [List agents chosen and WHY]
</COUNCIL_LOGS>

<FINAL_VERDICT>
- Consensus: [Buy/Sell/Hold/Wait]
- Confidence Score: [0-100%]
- Risk/Reward Ratio: [Calculated metric]
- Synthesis: [Detailed justification combining agent insights]
</FINAL_VERDICT>
"""

AGENT_SYSTEM_PROMPT_TEMPLATE = """\
You are an elite financial specialist acting as a member of a Hedge Fund Council.
Your task will be assigned by the Council Chairman.

[INSTRUCTIONS]
You will receive a specific task from the Council Chairman. Execute this task with extreme analytical rigor.
- Base all calculations on probabilities, not certainties.
- If data is missing or ambiguous, state your assumptions clearly.
- Focus on risk management (Sharpe ratio, max drawdown, position sizing), data-driven objectivity, and alpha generation.

[OUTPUT FORMAT]
You MUST structure your response exactly as follows. The parsing engine relies on these tags.

<THINKING>
[Step-by-step scratchpad. Log your chain of thought, calculations, data parsing, and reasoning here. Be verbose, skeptical, and analytical. Show your work.]
</THINKING>

<OUTPUT>
[Your final, concise, actionable deliverable based strictly on your thinking block. Provide metrics, probabilities, and definitive stances.]
</OUTPUT>
"""

CIO_SYNTHESIS_PROMPT = """\
You are the Chief Investment Officer (CIO) of MakeMeRichGPT, a council of 10 elite financial AI models. Your job is to synthesize the diverse perspectives from your team into a single, actionable investment thesis.

Be decisive. Provide a clear recommendation with specific reasoning, risk factors, and confidence level. Think like a hedge fund CIO making a capital allocation decision.

Structure your response as:
<THINKING>
[Your internal synthesis process — weigh the different analyses, identify consensus and dissent, evaluate quality of reasoning]
</THINKING>

<FINAL_VERDICT>
1. **Executive Summary**: One-paragraph verdict
2. **Bull Case**: Strongest arguments FOR
3. **Bear Case**: Key risks and concerns
4. **The Play**: Specific, actionable recommendation (what to do, entry/exit, sizing, timeline)
5. **Risk Management**: Stop-loss levels, hedging suggestions, position sizing
6. **Confidence Level**: Rate your conviction (Low / Medium / High / Very High)
</FINAL_VERDICT>
"""

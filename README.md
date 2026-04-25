# LLM Council — CouncilGPT

![llmcouncil](header.jpg)

This project is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions, acting as a Quantitative Hedge Fund Council. The key innovation is a LangGraph-orchestrated peer review system, preventing models from playing favorites and ensuring well-rounded financial analyses.

## Architecture & Data Flow

1. **Pre-Processing (Tools & Context)**: The user query is checked for URLs to scrape (BeautifulSoup4), web search intent (DuckDuckGo), or uploaded documents/images (PyPDF2, PyTesseract). A comprehensive `augmented_content` prompt is built with live data.
2. **Stage 0: Chairman Dispatch**: The Chairman model analyzes the query, determines how many agents to activate from the 10-member roster, and creates a tailored, dynamic system prompt for each agent.
3. **Stage 1: Individual Analyses**: The selected LLMs independently analyze the query with their custom roles. Responses are formatted into `<THINKING>` and `<OUTPUT>` blocks.
4. **Stage 2: Peer Review**: The individual responses are anonymized (Response A, Response B) and sent to the selected LLMs. They evaluate each other strictly on financial criteria (Accuracy, Actionability, Risk, Depth, Clarity) and rank them.
5. **Stage 3: CIO Synthesis**: The Chairman reviews the initial analyses and the peer rankings to produce a final, definitive investment thesis.

## Features

- **Stateless Memory**: Full conversation history is automatically injected into the API calls for true context awareness without breaking stateless REST design.
- **Dynamic Dispatching**: The Chairman dynamically assigns roles to agents based on the query complexity.
- **AI Image Generation**: Integrated Cloudflare Workers AI for inline image generation.
- **Rich Markdown Formatting**: Supports code highlighting, tables, and lists.
- **Token Usage Dashboard**: Live tracking of daily Groq API usage and token limits.
- **Thinking Timers**: Live spinners and precise timing metrics for each LangGraph stage.

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Provide a single Groq API key for all council members
GROQ_API_KEY="gsk_..."

# Required for Image Generation
CLOUDFLARE_API_TOKEN="your_token_here"
```

*Note: The Chairman and Title Generator currently reuse keys 1 and 7, respectively, as defined in `backend/config.py`.*

### 3. Customize the Council (Optional)

Edit `backend/config.py` to customize the `COUNCIL_MEMBERS` array and models. The default configuration uses a variety of open-source models available on Groq (LLaMA 3, Qwen, etc.).

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Tech Stack

- **Orchestration**: LangGraph (StateGraph)
- **Backend:** FastAPI (Python), async httpx, Groq API
- **Frontend:** React + Vite, react-markdown, Server-Sent Events (SSE)
- **Data Storage:** JSON-based conversation storage in `data/conversations/`
- **Scraping & Search**: BeautifulSoup4, DuckDuckGo (DDGS)
- **OCR/Docs**: pytesseract, PyPDF2

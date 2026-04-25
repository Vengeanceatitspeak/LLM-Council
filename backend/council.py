"""LangGraph-based Council orchestration for CouncilGPT.

Uses LangGraph StateGraph to build a multi-stage deliberation pipeline:
  1. Chairman analyzes query and dispatches to agents
  2. Agents respond with <THINKING> + <OUTPUT> structured format
  3. Peer review and ranking
  4. CIO synthesizes final verdict with <THINKING> + <FINAL_VERDICT>

All thinking is parsed and exposed to the frontend for transparency.
Token usage is tracked from actual Groq API responses.
"""

import re
import time
import asyncio
from typing import List, Dict, Any, Tuple, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END

from .groq_client import query_groq_model, query_groq_models_parallel
from .settings_manager import load_settings
from .config import (
    TITLE_GEN_MODEL,
)
import os


# ─── State Definition ──────────────────────────────────────────────────────────

class CouncilState(TypedDict):
    """State that flows through the LangGraph pipeline."""
    user_query: str
    conversation_history: List[Dict[str, str]]
    dispatch_plan: Dict[str, Any]
    stage1_results: List[Dict[str, Any]]
    stage2_results: List[Dict[str, Any]]
    stage3_result: Dict[str, Any]
    label_to_model: Dict[str, str]
    aggregate_rankings: List[Dict[str, Any]]
    errors: List[str]
    agent_count: int


# ─── Thinking Parser ───────────────────────────────────────────────────────────

def parse_thinking_and_output(raw_text: str) -> Dict[str, str]:
    """
    Parse <THINKING>...</THINKING> and <OUTPUT>...</OUTPUT> blocks
    from a model's response.

    Returns:
        Dict with 'thinking', 'output', and 'raw' keys
    """
    thinking = ""
    output = ""

    # Extract THINKING block
    thinking_match = re.search(
        r'<THINKING>(.*?)</THINKING>',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    if thinking_match:
        thinking = thinking_match.group(1).strip()

    # Extract OUTPUT block
    output_match = re.search(
        r'<OUTPUT>(.*?)</OUTPUT>',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    if output_match:
        output = output_match.group(1).strip()

    # Extract AGENT_CONCLUSION block (alternative tag)
    if not output:
        conclusion_match = re.search(
            r'<AGENT_CONCLUSION>(.*?)</AGENT_CONCLUSION>',
            raw_text,
            re.DOTALL | re.IGNORECASE
        )
        if conclusion_match:
            output = conclusion_match.group(1).strip()

    # Extract FINAL_VERDICT block
    verdict_match = re.search(
        r'<FINAL_VERDICT>(.*?)</FINAL_VERDICT>',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    if verdict_match:
        output = verdict_match.group(1).strip()

    # If no structured output found, treat entire text as output
    if not output and not thinking:
        output = raw_text.strip()
    elif not output:
        # Had thinking but no output tag — everything after thinking is output
        output = raw_text.replace(thinking_match.group(0), "").strip() if thinking_match else raw_text.strip()

    return {
        "thinking": thinking,
        "output": output,
        "raw": raw_text,
    }


# ─── LangGraph Node Functions ──────────────────────────────────────────────────

import json

async def node_stage0_dispatch(state: CouncilState) -> dict:
    """
    Stage 0: Chairman decomposes the query and dispatches to specific agents.
    """
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    
    # Prepend history if available
    messages = conversation_history + [{"role": "user", "content": user_query}]

    settings = load_settings()
    members_list = settings.get("members", [])
    agent_count = len(members_list)
    chairman_prompt = settings.get("chairman_prompt", "")
    chairman_model = settings.get("chairman_model", "llama-3.3-70b-versatile")
    chairman_api_key = os.getenv("GROQ_API_KEY", "")
    
    # Dynamically inject the agent count into the prompt
    system_prompt = chairman_prompt.replace(
        "{agent_count}", str(agent_count)
    )

    response = await query_groq_model(
        api_key=chairman_api_key,
        model=chairman_model,
        messages=messages,
        system_prompt=system_prompt,
    )
    
    dispatch_plan = {}
    if response and response.get("content"):
        content = response["content"].strip()
        # Clean up possible markdown fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            dispatch_plan = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing Chairman dispatch JSON: {e}")
            dispatch_plan = {"error": "Failed to parse dispatch plan"}
            
    return {"dispatch_plan": dispatch_plan}


async def node_stage1_collect(state: CouncilState) -> dict:
    """
    Stage 1: Dispatched council members analyze the query independently.
    Each produces <THINKING> + <OUTPUT> structured response.
    """
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    dispatch_plan = state.get("dispatch_plan", {})
    
    messages = conversation_history + [{"role": "user", "content": user_query}]
    
    tasks = dispatch_plan.get("council_tasks", [])
    
    # If chairman failed, fallback to querying a few default agents
    if not tasks:
        tasks = [
            {"agent_id": i + 1, "assigned_role": m.get("role", "Analyst"), "task": "General analysis", "output_format": "Standard", "constraints": "None"}
            for i, m in enumerate(members_list)
        ]

    # Map member IDs and create dynamic system prompts
    selected_members = []
    member_prompts = {}
    
    settings = load_settings()
    members_list = settings.get("members", [])
    default_model = settings.get("default_model", "llama-3.3-70b-versatile")
    agent_count = len(members_list)
    
    # Match tasks to agents by index (agents are stateless slots)
    for i, t in enumerate(tasks):
        member = members_list[i % len(members_list)] if members_list else None
        if member:
            # Ensure model is set (fall back to default)
            if not member.get("model"):
                member["model"] = default_model
            selected_members.append(member)
            agent_prompt = member.get("system_prompt", "")
            dynamic_prompt = agent_prompt + f"\n\n[YOUR SPECIFIC ASSIGNMENT]\nROLE: {t.get('assigned_role')}\nTASK: {t.get('task')}\nOUTPUT FORMAT: {t.get('output_format')}\nCONSTRAINTS: {t.get('constraints')}"
            member_prompts[member["id"]] = dynamic_prompt
            
    if not selected_members and members_list:
        selected_members = [members_list[0]]
        if not selected_members[0].get("model"):
            selected_members[0]["model"] = default_model
        member_prompts[members_list[0]["id"]] = members_list[0].get("system_prompt", "")

    # Query dispatched members in parallel, each with their own dynamic system prompt
    global_api_key = os.getenv("GROQ_API_KEY", "")
    tasks_coros = [
        query_groq_model(
            api_key=member.get("api_key") or global_api_key,
            model=member["model"],
            messages=messages,
            system_prompt=member_prompts[member["id"]]
        ) for member in selected_members
    ]
    
    results = await asyncio.gather(*tasks_coros, return_exceptions=True)
    
    responses = {}
    for member, res in zip(selected_members, results):
        if not isinstance(res, Exception) and res is not None:
            responses[member["id"]] = res

    # Format results with parsed thinking
    stage1_results = []
    for member in selected_members:
        response = responses.get(member["id"])
        if response is not None and response.get("content"):
            parsed = parse_thinking_and_output(response["content"])
            usage = response.get("usage", {})
            stage1_results.append({
                "member_id": member["id"],
                "model": member["model"],
                "display_name": member.get("role", member.get("display_name", member["id"])),
                "color": member.get("color", "#3b82f6"),
                "thinking": parsed["thinking"],
                "output": parsed["output"],
                "response": response["content"],
                "tokens": usage,
            })

    return {"stage1_results": stage1_results}


async def node_stage2_review(state: CouncilState) -> dict:
    """
    Stage 2: Each model ranks the anonymized responses from Stage 1.
    Finance-specific evaluation criteria.
    """
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    stage1_results = state["stage1_results"]

    if not stage1_results:
        return {
            "stage2_results": [],
            "label_to_model": {},
            "aggregate_rankings": [],
        }

    # Create anonymized labels
    labels = [chr(65 + i) for i in range(len(stage1_results))]

    # Map label -> member info
    label_to_model = {
        f"Response {label}": result["display_name"]
        for label, result in zip(labels, stage1_results)
    }

    # Build ranking prompt using OUTPUT only (not thinking)
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['output']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are a senior reviewer evaluating different analyses for the following question:

Question: {user_query}

Here are the responses from different experts (anonymized):

{responses_text}

Your task:
1. Evaluate each response on these criteria:
   - **Accuracy**: Are the concepts, data, and reasoning correct?
   - **Depth**: Is the analysis thorough with supporting evidence?
   - **Clarity**: Is it well-structured and easy to understand?
   - **Actionability**: Does it provide specific, useful insights or recommendations?

2. Then, at the very end, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format:

Response A provides solid fundamental analysis...
Response B offers good perspective but lacks actionable steps...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = conversation_history + [{"role": "user", "content": ranking_prompt}]

    settings = load_settings()
    members_list = settings.get("members", [])

    # Identify which members actually participated in stage 1
    participated_ids = {r["member_id"] for r in stage1_results}
    selected_members = [m for m in members_list if m["id"] in participated_ids]
    
    if not selected_members:
        selected_members = members_list

    # Get rankings from the selected council members in parallel
    responses = await query_groq_models_parallel(selected_members, messages)

    stage2_results = []
    for member in selected_members:
        response = responses.get(member["id"])
        if response is not None and response.get("content"):
            full_text = response["content"]
            parsed = parse_ranking_from_text(full_text)
            usage = response.get("usage", {})
            stage2_results.append({
                "member_id": member["id"],
                "model": member["model"],
                "display_name": member.get("role", member.get("display_name", member["id"])),
                "ranking": full_text,
                "parsed_ranking": parsed,
                "tokens": usage,
            })

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    return {
        "stage2_results": stage2_results,
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
    }


async def node_stage3_synthesize(state: CouncilState) -> dict:
    """
    Stage 3: CIO synthesizes final verdict using <THINKING> + <FINAL_VERDICT>.
    """
    user_query = state["user_query"]
    conversation_history = state.get("conversation_history", [])
    stage1_results = state["stage1_results"]
    stage2_results = state["stage2_results"]
    dispatch_plan = state.get("dispatch_plan", {})

    # Build comprehensive context for CIO
    stage1_text = "\n\n".join([
        f"**{result['display_name']}**:\n{result['output']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"**{result['display_name']}**:\n{result['ranking']}"
        for result in stage2_results
    ])
    
    synthesis_instruction = dispatch_plan.get("synthesis_instruction", "Be decisive. Your output should be clear and actionable.")

    chairman_prompt = f"""Your multi-agent expert council has analyzed the following question and peer-reviewed each other's work.

Original Question: {user_query}

STAGE 1 — Individual Analyses:
{stage1_text}

STAGE 2 — Peer Rankings & Evaluations:
{stage2_text}

As Lead Synthesizer, synthesize all perspectives into a DEFINITIVE conclusion.
{synthesis_instruction}"""

    messages = conversation_history + [{"role": "user", "content": chairman_prompt}]

    settings = load_settings()
    agent_count = len(settings.get("members", []))
    synthesizer_prompt = settings.get("synthesizer_prompt", "")
    synthesizer_model = settings.get("synthesizer_model", "llama-3.3-70b-versatile")
    synthesizer_api_key = os.getenv("GROQ_API_KEY", "")

    system_prompt = synthesizer_prompt

    response = await query_groq_model(
        api_key=synthesizer_api_key,
        model=synthesizer_model,
        messages=messages,
        system_prompt=system_prompt,
    )

    if response is None or not response.get("content"):
        return {
            "stage3_result": {
                "model": synthesizer_model,
                "display_name": "Lead Synthesizer",
                "thinking": "",
                "output": "Error: Unable to generate final synthesis.",
                "response": "Error: Unable to generate final synthesis.",
                "tokens": {},
            }
        }

    parsed = parse_thinking_and_output(response["content"])
    usage = response.get("usage", {})

    return {
        "stage3_result": {
            "model": synthesizer_model,
            "display_name": "Lead Synthesizer",
            "thinking": parsed["thinking"],
            "output": parsed["output"],
            "response": response["content"],
            "tokens": usage,
        }
    }


# ─── Build the LangGraph ───────────────────────────────────────────────────────

def build_council_graph() -> StateGraph:
    """Build the LangGraph StateGraph for the council process."""
    workflow = StateGraph(CouncilState)

    # Add nodes
    workflow.add_node("stage0_dispatch", node_stage0_dispatch)
    workflow.add_node("stage1_collect", node_stage1_collect)
    workflow.add_node("stage2_review", node_stage2_review)
    workflow.add_node("stage3_synthesize", node_stage3_synthesize)

    # Define the execution flow
    workflow.set_entry_point("stage0_dispatch")
    workflow.add_edge("stage0_dispatch", "stage1_collect")
    workflow.add_edge("stage1_collect", "stage2_review")
    workflow.add_edge("stage2_review", "stage3_synthesize")
    workflow.add_edge("stage3_synthesize", END)

    return workflow.compile()


# Compile the graph once at module level
council_graph = build_council_graph()


# ─── Public API ─────────────────────────────────────────────────────────────────

async def stage1_collect_responses(user_query: str, conversation_history: List[Dict[str, str]] = None, agent_count: int = 10) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Stage 0 & 1: Dispatch agents and collect individual responses.

    Args:
        user_query: The user's question
        conversation_history: List of previous messages

    Returns:
        Tuple of (stage1_results, dispatch_plan)
    """
    result = await council_graph.ainvoke({
        "user_query": user_query,
        "conversation_history": conversation_history or [],
        "dispatch_plan": {},
        "stage1_results": [],
        "stage2_results": [],
        "stage3_result": {},
        "label_to_model": {},
        "aggregate_rankings": [],
        "errors": [],
        "agent_count": agent_count,
    })
    return result["stage1_results"], result.get("dispatch_plan", {})


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.
    """
    result = await node_stage2_review({
        "user_query": user_query,
        "conversation_history": conversation_history or [],
        "dispatch_plan": {},
        "stage1_results": stage1_results,
        "stage2_results": [],
        "stage3_result": {},
        "label_to_model": {},
        "aggregate_rankings": [],
        "errors": [],
    })
    return result["stage2_results"], result["label_to_model"]


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    dispatch_plan: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Stage 3: CIO synthesizes final investment thesis.
    """
    result = await node_stage3_synthesize({
        "user_query": user_query,
        "conversation_history": conversation_history or [],
        "dispatch_plan": dispatch_plan or {},
        "stage1_results": stage1_results,
        "stage2_results": stage2_results,
        "stage3_result": {},
        "label_to_model": {},
        "aggregate_rankings": [],
        "errors": [],
    })
    return result["stage3_result"]


async def run_full_council(user_query: str, conversation_history: List[Dict[str, str]] = None, agent_count: int = 10) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process using LangGraph.
    """
    initial_state = {
        "user_query": user_query,
        "conversation_history": conversation_history or [],
        "dispatch_plan": {},
        "stage1_results": [],
        "stage2_results": [],
        "stage3_result": {},
        "label_to_model": {},
        "aggregate_rankings": [],
        "errors": [],
        "agent_count": agent_count,
    }

    # Run the graph
    final_state = await council_graph.ainvoke(initial_state)

    stage1_results = final_state.get("stage1_results", [])
    stage2_results = final_state.get("stage2_results", [])
    stage3_result = final_state.get("stage3_result", {})

    if not stage1_results:
        return [], [], {
            "model": "error",
            "display_name": "System",
            "thinking": "",
            "output": "All models failed to respond. Please try again.",
            "response": "All models failed to respond. Please try again.",
            "tokens": {},
        }, {}

    metadata = {
        "label_to_model": final_state.get("label_to_model", {}),
        "aggregate_rankings": final_state.get("aggregate_rankings", []),
        "dispatch_plan": final_state.get("dispatch_plan", {})
    }

    return stage1_results, stage2_results, stage3_result, metadata


# ─── Ranking Parsers ───────────────────────────────────────────────────────────

def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.
    """
    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.
    """
    from collections import defaultdict

    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    settings = load_settings()
    members_list = settings.get("members", [])
    # Build member lookup
    member_lookup = {m["display_name"]: m for m in members_list}

    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            member = member_lookup.get(model, {})
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "display_name": model,
                "model": member.get("model", model),
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions),
            })

    aggregate.sort(key=lambda x: x['average_rank'])
    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.
    """
    title_prompt = (
        "Generate a very short title (3-5 words maximum) that summarizes "
        "the following question. The title should be concise, "
        "descriptive, and relevant. Do not use quotes or punctuation.\n\n"
        f"Question: {user_query}\n\nTitle:"
    )

    messages = [{"role": "user", "content": title_prompt}]

    response = await query_groq_model(
        api_key=os.getenv("GROQ_API_KEY", ""),
        model=TITLE_GEN_MODEL,
        messages=messages,
        timeout=30.0,
    )

    if response is None:
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()
    title = title.strip('"\'')

    if len(title) > 50:
        title = title[:47] + "..."

    return title

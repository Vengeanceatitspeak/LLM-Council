"""3-stage LLM Council orchestration for MakeMeRichGPT."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL, COUNCIL_ROLES, CHAIRMAN_SYSTEM_PROMPT


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.
    Each model responds with their finance-specialist persona.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model', 'role', and 'response' keys
    """
    messages = [{"role": "user", "content": user_query}]

    # Build system prompts dict for each model
    system_prompts = {
        model: role_info["system_prompt"]
        for model, role_info in COUNCIL_ROLES.items()
    }

    # Query all models in parallel with their personas
    responses = await query_models_parallel(COUNCIL_MODELS, messages, system_prompts=system_prompts)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            role_info = COUNCIL_ROLES.get(model, {})
            stage1_results.append({
                "model": model,
                "role": role_info.get("role", "Analyst"),
                "icon": role_info.get("icon", "💼"),
                "color": role_info.get("color", "#888"),
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.
    Evaluation criteria are finance-specific.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt with finance-specific criteria
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are a senior portfolio manager evaluating different financial analyses for the following question:

Question: {user_query}

Here are the responses from different analysts (anonymized):

{responses_text}

Your task:
1. Evaluate each response on these FINANCE-SPECIFIC criteria:
   - **Accuracy**: Are the financial concepts, data, and reasoning correct?
   - **Actionability**: Does it provide specific, tradeable insights (entry/exit, targets, sizing)?
   - **Risk Awareness**: Does it address downside risks, stop-losses, or hedging?
   - **Depth**: Is the analysis thorough with supporting evidence?
   - **Clarity**: Is it well-structured and easy to act upon?

2. Then, at the very end, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format:

Response A provides solid fundamental analysis with specific price targets...
Response B offers good macro perspective but lacks actionable trade setups...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            role_info = COUNCIL_ROLES.get(model, {})
            stage2_results.append({
                "model": model,
                "role": role_info.get("role", "Analyst"),
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: CIO synthesizes final investment thesis.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model', 'role', and 'response' keys
    """
    # Build comprehensive context for CIO
    stage1_text = "\n\n".join([
        f"**{result.get('role', 'Analyst')}** ({result['model']}):\n{result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"**{result.get('role', 'Analyst')}** ({result['model']}):\n{result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chief Investment Officer (CIO) of MakeMeRichGPT. Your council of 10 elite financial specialists has analyzed the following question and peer-reviewed each other's work.

Original Question: {user_query}

STAGE 1 — Individual Specialist Analyses:
{stage1_text}

STAGE 2 — Peer Rankings & Evaluations:
{stage2_text}

As CIO, synthesize all perspectives into a DEFINITIVE investment thesis:

1. **Executive Summary**: One-paragraph verdict
2. **Bull Case**: Strongest arguments FOR
3. **Bear Case**: Key risks and concerns
4. **The Play**: Specific, actionable recommendation (what to do, entry/exit, sizing, timeline)
5. **Risk Management**: Stop-loss levels, hedging suggestions, position sizing
6. **Confidence Level**: Rate your conviction (Low / Medium / High / Very High)

Be decisive. Your investors are paying for alpha, not hedged language."""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model with CIO persona
    response = await query_model(CHAIRMAN_MODEL, messages, system_prompt=CHAIRMAN_SYSTEM_PROMPT)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "role": "Chief Investment Officer",
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "role": "Chief Investment Officer",
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name, role, and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            role_info = COUNCIL_ROLES.get(model, {})
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "role": role_info.get("role", "Analyst"),
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following financial question.
The title should be concise, descriptive, and finance-related. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "role": "System",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata

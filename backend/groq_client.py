"""Groq API client for making LLM requests.

Each council member has their own individual Groq API key.
"""

import asyncio
from typing import List, Dict, Any, Optional
from groq import AsyncGroq


async def query_groq_model(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via Groq API using its individual API key.

    Args:
        api_key: Groq API key for this specific model
        model: Groq model identifier (e.g., "llama-3.3-70b-versatile")
        messages: List of message dicts with 'role' and 'content'
        system_prompt: Optional system message to prepend
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' key, or None if failed
    """
    # Prepend system prompt if provided
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    try:
        client = AsyncGroq(api_key=api_key, timeout=timeout)
        response = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=0.7,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        return {"content": content}

    except Exception as e:
        print(f"Error querying Groq model {model}: {e}")
        return None


async def query_groq_models_parallel(
    members: List[Dict[str, Any]],
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple Groq models in parallel, each with their own API key.

    Args:
        members: List of council member dicts (each has 'api_key', 'model', 'id')
        messages: List of message dicts to send to each model
        system_prompt: Optional system prompt for all models

    Returns:
        Dict mapping member_id to response dict (or None if failed)
    """
    tasks = []
    for member in members:
        tasks.append(
            query_groq_model(
                api_key=member["api_key"],
                model=member["model"],
                messages=messages,
                system_prompt=system_prompt,
            )
        )

    responses = await asyncio.gather(*tasks)

    return {
        member["id"]: response
        for member, response in zip(members, responses)
    }

"""Cloudflare Workers AI image generation module for MakeMeRichGPT.

Uses the Cloudflare Workers AI REST API to generate images
via the FLUX.1 [schnell] model (fast, free tier).
"""

import os
import base64
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "8cb75e3ccc02647fff32bd6f3f9738c5")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

# Image model — FLUX.1 [schnell] is fast and free
IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"

IMAGE_SAVE_DIR = "data/generated_images"


def ensure_image_dir():
    """Ensure image storage directory exists."""
    Path(IMAGE_SAVE_DIR).mkdir(parents=True, exist_ok=True)


async def generate_image(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Generate an image using Cloudflare Workers AI.

    Args:
        prompt: Text description of the image to generate

    Returns:
        Dict with 'image_base64', 'filename', 'prompt' or None on failure
    """
    if not CLOUDFLARE_API_TOKEN:
        return {
            "error": True,
            "message": "Cloudflare API Token not configured. Add CLOUDFLARE_API_TOKEN to your .env file.",
        }

    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{IMAGE_MODEL}"

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "num_steps": 4,  # schnell is optimized for 4 steps
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            error_text = response.text
            print(f"Cloudflare API error: {response.status_code} - {error_text}")
            return {
                "error": True,
                "message": f"Image generation failed: HTTP {response.status_code}",
            }

        # The response is raw image bytes (PNG)
        image_bytes = response.content

        # Check if response is JSON (error)
        try:
            json_resp = response.json()
            if not json_resp.get("success", True):
                errors = json_resp.get("errors", [])
                msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
                return {"error": True, "message": f"Image generation failed: {msg}"}
        except Exception:
            pass  # Not JSON, it's raw image bytes — that's good

        # Convert to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Save to disk
        ensure_image_dir()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"img_{timestamp}.png"
        filepath = os.path.join(IMAGE_SAVE_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        return {
            "error": False,
            "image_base64": image_b64,
            "filename": filename,
            "filepath": filepath,
            "prompt": prompt,
        }

    except Exception as e:
        print(f"Error generating image: {e}")
        return {
            "error": True,
            "message": f"Image generation failed: {str(e)}",
        }


def is_image_generation_available() -> bool:
    """Check if image generation is configured."""
    return bool(CLOUDFLARE_API_TOKEN)

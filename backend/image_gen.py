"""Cloudflare Workers AI image generation module for CouncilGPT.

Uses the Cloudflare Workers AI REST API to generate images
via the FLUX.1 [schnell] model (fast, free tier).

Includes comprehensive error logging and network request tracing.
"""

import os
import base64
import httpx
import traceback
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
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
    # ─── Pre-flight checks ──────────────────────────────────────────────
    if not CLOUDFLARE_API_TOKEN:
        print("[IMAGE_GEN] ERROR: CLOUDFLARE_API_TOKEN is empty or not set in .env")
        return {
            "error": True,
            "message": "Cloudflare API Token not configured. Add CLOUDFLARE_API_TOKEN to your .env file.",
        }

    if not CLOUDFLARE_ACCOUNT_ID:
        print("[IMAGE_GEN] ERROR: CLOUDFLARE_ACCOUNT_ID is empty or not set in .env")
        return {
            "error": True,
            "message": "Cloudflare Account ID not configured. Add CLOUDFLARE_ACCOUNT_ID to your .env file.",
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

    # ─── Network request tracing ────────────────────────────────────────
    print(f"\n[IMAGE_GEN] ═══════════════════════════════════════════")
    print(f"[IMAGE_GEN] Generating image for prompt: {prompt[:100]}...")
    print(f"[IMAGE_GEN] Endpoint: {url}")
    print(f"[IMAGE_GEN] Account ID: {CLOUDFLARE_ACCOUNT_ID[:12]}...")
    print(f"[IMAGE_GEN] Token prefix: {CLOUDFLARE_API_TOKEN[:12]}...")
    print(f"[IMAGE_GEN] Payload: {payload}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("[IMAGE_GEN] Sending POST request...")
            response = await client.post(url, headers=headers, json=payload)

        print(f"[IMAGE_GEN] Response status: {response.status_code}")
        print(f"[IMAGE_GEN] Response headers: {dict(response.headers)}")
        print(f"[IMAGE_GEN] Response content-type: {response.headers.get('content-type', 'N/A')}")
        print(f"[IMAGE_GEN] Response size: {len(response.content)} bytes")

        if response.status_code != 200:
            error_text = response.text[:500]
            print(f"[IMAGE_GEN] ERROR — Non-200 response: {error_text}")
            return {
                "error": True,
                "message": f"Image generation failed: HTTP {response.status_code} — {error_text[:200]}",
            }

        # Check content type to determine response format
        content_type = response.headers.get("content-type", "")

        # If JSON response, check for errors
        if "application/json" in content_type:
            try:
                json_resp = response.json()
                print(f"[IMAGE_GEN] JSON response: {str(json_resp)[:500]}")

                if not json_resp.get("success", True):
                    errors = json_resp.get("errors", [])
                    msg = errors[0].get("message", "Unknown error") if errors else "Unknown error"
                    print(f"[IMAGE_GEN] API error: {msg}")
                    return {"error": True, "message": f"Image generation failed: {msg}"}

                # Some Cloudflare models return base64 in JSON
                if "result" in json_resp and "image" in json_resp["result"]:
                    image_b64 = json_resp["result"]["image"]
                    image_bytes = base64.b64decode(image_b64)
                    print(f"[IMAGE_GEN] Got image from JSON result field ({len(image_bytes)} bytes)")
                else:
                    print(f"[IMAGE_GEN] Unexpected JSON structure: {list(json_resp.keys())}")
                    return {"error": True, "message": "Unexpected API response format"}
            except Exception as json_err:
                print(f"[IMAGE_GEN] JSON parse error (treating as raw bytes): {json_err}")
                image_bytes = response.content
        else:
            # Raw image bytes (PNG) — this is the expected response for FLUX
            image_bytes = response.content
            print(f"[IMAGE_GEN] Got raw image bytes ({len(image_bytes)} bytes)")

        # Validate we got actual image data
        if len(image_bytes) < 100:
            print(f"[IMAGE_GEN] WARNING: Suspiciously small response ({len(image_bytes)} bytes)")
            return {
                "error": True,
                "message": f"Image generation returned suspiciously small data ({len(image_bytes)} bytes)",
            }

        # Convert to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Save to disk
        ensure_image_dir()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"img_{timestamp}.png"
        filepath = os.path.join(IMAGE_SAVE_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        print(f"[IMAGE_GEN] Image saved: {filepath}")
        print(f"[IMAGE_GEN] ═══════════════════════════════════════════\n")

        return {
            "error": False,
            "image_base64": image_b64,
            "filename": filename,
            "filepath": filepath,
            "prompt": prompt,
        }

    except httpx.ConnectError as e:
        print(f"[IMAGE_GEN] CONNECTION ERROR: Cannot reach Cloudflare API — {e}")
        print("[IMAGE_GEN] Checklist:")
        print("  1. Is your internet connection working?")
        print("  2. Is api.cloudflare.com reachable? Try: curl -I https://api.cloudflare.com")
        print("  3. Is there a firewall/proxy blocking the request?")
        traceback.print_exc()
        return {
            "error": True,
            "message": f"Cannot connect to Cloudflare API: {str(e)}",
        }

    except httpx.TimeoutException as e:
        print(f"[IMAGE_GEN] TIMEOUT: Request to Cloudflare timed out — {e}")
        traceback.print_exc()
        return {
            "error": True,
            "message": "Image generation timed out (60s limit). Try a simpler prompt.",
        }

    except Exception as e:
        print(f"[IMAGE_GEN] UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return {
            "error": True,
            "message": f"Image generation failed: {str(e)}",
        }


def is_image_generation_available() -> bool:
    """Check if image generation is configured."""
    available = bool(CLOUDFLARE_API_TOKEN) and bool(CLOUDFLARE_ACCOUNT_ID)
    if not available:
        print("[IMAGE_GEN] Image generation NOT available — missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID")
    return available

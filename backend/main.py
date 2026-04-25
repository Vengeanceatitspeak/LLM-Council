"""FastAPI backend for CouncilGPT — Multi-Agent Expert Council."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import time
import os
from pathlib import Path

from . import storage
from .settings_manager import load_settings, save_settings
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
)
from .config import TITLE_GEN_MODEL
from .web_scraper import scrape_url, search_web, detect_urls, detect_search_intent
from .documents import process_upload, get_upload_history, search_upload_memory
from .image_gen import generate_image, is_image_generation_available

app = FastAPI(title="CouncilGPT API")

# Enable CORS for local development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated images as static files
IMAGE_DIR = "data/generated_images"
UPLOAD_DIR = "data/uploads"
Path(IMAGE_DIR).mkdir(parents=True, exist_ok=True)
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


# ─── Request / Response Models ───────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    image_mode: bool = False


class RenameConversationRequest(BaseModel):
    """Request to rename a conversation."""
    title: str


class SearchRequest(BaseModel):
    """Request to search the web."""
    query: str
    max_results: int = 5


class ScrapeRequest(BaseModel):
    """Request to scrape a URL."""
    url: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


# ─── Health & Info Endpoints ─────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "CouncilGPT API"}


@app.get("/api/council/members")
async def get_council_members():
    """Get info about all council members."""
    settings = load_settings()
    members = []
    for member in settings.get("members", []):
        members.append({
            "id": member["id"],
            "model": member["model"],
            "display_name": member["display_name"],
            "color": member["color"],
        })
    return {
        "members": members,
        "chairman": {
            "model": settings.get("chairman_model", "llama-3.3-70b-versatile"),
            "display_name": "Chairman",
        },
        "total": len(members),
        "image_gen_available": is_image_generation_available(),
    }


# ─── Settings Endpoints ─────────────────────────────────────────────────────

@app.get("/api/settings/council")
async def get_settings():
    """Get the current council configuration."""
    return load_settings()

@app.put("/api/settings/council")
async def update_settings(request: dict):
    """Update the council configuration."""
    if save_settings(request):
        return {"status": "ok"}
    raise HTTPException(status_code=500, detail="Failed to save settings")


# ─── Usage / Credits Endpoints ──────────────────────────────────────────────

@app.get("/api/usage")
async def get_usage():
    """Get current daily credit and token usage."""
    return storage.get_daily_usage()


# ─── Conversation CRUD Endpoints ────────────────────────────────────────────

@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, request: RenameConversationRequest):
    """Rename a conversation."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    storage.update_conversation_title(conversation_id, request.title)
    return {"status": "ok", "title": request.title}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok"}


# ─── File Upload Endpoint ───────────────────────────────────────────────────

@app.post("/api/conversations/{conversation_id}/upload")
async def upload_file(
    conversation_id: str,
    file: UploadFile = File(...),
):
    """Upload a file (PDF, image, text) and extract its text content."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Read file bytes
    file_bytes = await file.read()

    # Process the upload
    result = process_upload(
        filename=file.filename or "unknown",
        file_bytes=file_bytes,
        conversation_id=conversation_id,
    )

    return {
        "status": "ok",
        "filename": result["filename"],
        "file_type": result["file_type"],
        "extracted_text": result["extracted_text"],
        "size_bytes": result["size_bytes"],
    }


@app.get("/api/conversations/{conversation_id}/uploads")
async def get_conversation_uploads(conversation_id: str):
    """Get upload history for a conversation."""
    uploads = get_upload_history(conversation_id)
    return {
        "uploads": [
            {
                "filename": u["filename"],
                "file_type": u["file_type"],
                "uploaded_at": u["uploaded_at"],
                "size_bytes": u["size_bytes"],
            }
            for u in uploads
        ]
    }


# ─── Web Scraper & Search Endpoints ─────────────────────────────────────────

@app.post("/api/search")
async def web_search(request: SearchRequest):
    """Search the web using DuckDuckGo."""
    results = search_web(request.query, request.max_results)
    return {"results": results, "query": request.query}


@app.post("/api/scrape")
async def scrape_website(request: ScrapeRequest):
    """Scrape a URL and return its text content."""
    result = await scrape_url(request.url)
    if result is None:
        raise HTTPException(status_code=400, detail="Failed to scrape URL")
    return result


# ─── Image Generation Endpoint ──────────────────────────────────────────────

@app.post("/api/generate-image")
async def generate_image_endpoint(request: SendMessageRequest):
    """Generate an image using Cloudflare Workers AI."""
    result = await generate_image(request.content)

    if result is None:
        raise HTTPException(status_code=500, detail="Image generation failed")

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("message", "Image generation failed"))

    return {
        "image_base64": result["image_base64"],
        "filename": result["filename"],
        "prompt": result["prompt"],
    }


# Serve generated images
@app.get("/api/images/{filename}")
async def get_image(filename: str):
    """Serve a generated image."""
    filepath = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath, media_type="image/png")


def build_conversation_history(conversation: dict, max_turns: int = 3) -> List[Dict[str, str]]:
    """Build a standard message history from the custom conversation schema."""
    history = []
    messages = conversation.get("messages", [])
    
    # We want the last `max_turns` turns (user + assistant pairs)
    recent_messages = messages[-(max_turns * 2):]
    
    for msg in recent_messages:
        if msg["role"] == "user":
            history.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            # Extract the final output from stage3
            content = "Assistant response unavailable"
            if "stage3" in msg and isinstance(msg["stage3"], dict):
                content = msg["stage3"].get("output", "No response generated.")
            history.append({"role": "assistant", "content": content})
            
    return history


# ─── Message Endpoints ──────────────────────────────────────────────────────

@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check credits
    if not storage.check_credit_available():
        raise HTTPException(
            status_code=429,
            detail="Daily credit limit reached. Please try again tomorrow."
        )

    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Build conversation history before appending the current message
    history = build_conversation_history(conversation)

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # Increment usage
    storage.increment_usage()

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process via LangGraph
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        conversation_history=history,
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


def _sum_tokens(results_list):
    """Sum up total tokens from a list of stage results."""
    total = 0
    for r in results_list:
        tokens = r.get("tokens", {})
        total += tokens.get("total_tokens", 0)
    return total


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    Supports image_mode for generating images alongside text.
    Includes timing data for each stage.
    """
    # Check credits
    if not storage.check_credit_available():
        raise HTTPException(
            status_code=429,
            detail="Daily credit limit reached. Please try again tomorrow."
        )

    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        total_tokens = 0
        overall_start = time.time()

        try:
            # Build conversation history before appending the current message
            history = build_conversation_history(conversation)

            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # ─── Pre-processing: URL scraping and search ───────────────────
            augmented_content = request.content
            web_context = ""

            # Check for URLs in the message
            urls = detect_urls(request.content)
            if urls:
                scrape_start = time.time()
                yield f"data: {json.dumps({'type': 'web_scrape_start', 'data': {'urls': urls}})}\n\n"
                for url in urls[:3]:  # Limit to 3 URLs
                    scraped = await scrape_url(url)
                    if scraped:
                        web_context += f"\n\n[LIVE WEB DATA — scraped from: {scraped['title']} ({url})]:\n{scraped['text']}\n"
                scrape_duration = round(time.time() - scrape_start, 2)
                yield f"data: {json.dumps({'type': 'web_scrape_complete', 'data': {'duration_sec': scrape_duration}})}\n\n"

            # Check for search intent
            elif detect_search_intent(request.content):
                search_start = time.time()
                yield f"data: {json.dumps({'type': 'web_search_start'})}\n\n"
                results = search_web(request.content, max_results=5)
                if results:
                    web_context = "\n\n[LIVE WEB SEARCH RESULTS — fetched just now]:\n"
                    for r in results:
                        web_context += f"- {r['title']}: {r['body']} (Source: {r['href']})\n"
                search_duration = round(time.time() - search_start, 2)
                yield f"data: {json.dumps({'type': 'web_search_complete', 'data': {'count': len(results), 'duration_sec': search_duration}})}\n\n"

            # Check for document memory references
            upload_context = ""
            uploads = get_upload_history(conversation_id)
            if uploads:
                upload_context = "\n\n[UPLOADED DOCUMENT DATA — extracted from user's files]:\n"
                for u in uploads[-5:]:  # Last 5 uploads
                    upload_context += f"\n--- File: {u['filename']} ---\n{u.get('extracted_text', '')[:2000]}\n"

            # Augment the prompt with web + document context
            if web_context or upload_context:
                augmented_content = f"{request.content}\n\n=== REAL-TIME DATA (USE THIS — DO NOT SAY YOU LACK ACCESS) ==={web_context}{upload_context}\n=== END REAL-TIME DATA ==="

            # ─── Image generation (if image_mode is on) ────────────────────
            if request.image_mode:
                img_start = time.time()
                yield f"data: {json.dumps({'type': 'image_gen_start'})}\n\n"
                img_result = await generate_image(request.content)
                img_duration = round(time.time() - img_start, 2)
                if img_result and not img_result.get("error"):
                    yield f"data: {json.dumps({'type': 'image_gen_complete', 'data': {'image_base64': img_result['image_base64'], 'filename': img_result['filename'], 'prompt': request.content, 'duration_sec': img_duration}})}\n\n"
                else:
                    error_msg = img_result.get("message", "Image generation failed") if img_result else "Image generation failed"
                    yield f"data: {json.dumps({'type': 'image_gen_error', 'data': {'message': error_msg, 'duration_sec': img_duration}})}\n\n"

            # ─── Usage update ──────────────────────────────────────────────
            usage = storage.increment_usage()
            yield f"data: {json.dumps({'type': 'usage_update', 'data': usage})}\n\n"

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses (and dispatch)
            stage1_start = time.time()
            yield f"data: {json.dumps({'type': 'stage1_start', 'data': {'timestamp': stage1_start}})}\n\n"
            stage1_results, dispatch_plan = await stage1_collect_responses(
                augmented_content, 
                conversation_history=history,
            )

            # Count actual tokens from stage 1
            stage1_tokens = _sum_tokens(stage1_results)
            total_tokens += stage1_tokens
            stage1_duration = round(time.time() - stage1_start, 2)

            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results, 'timing': {'duration_sec': stage1_duration, 'tokens': stage1_tokens}})}\n\n"

            # Stage 2: Collect rankings
            stage2_start = time.time()
            yield f"data: {json.dumps({'type': 'stage2_start', 'data': {'timestamp': stage2_start}})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(augmented_content, stage1_results, conversation_history=history)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

            stage2_tokens = _sum_tokens(stage2_results)
            total_tokens += stage2_tokens
            stage2_duration = round(time.time() - stage2_start, 2)

            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}, 'timing': {'duration_sec': stage2_duration, 'tokens': stage2_tokens}})}\n\n"

            # Stage 3: Synthesize final answer
            stage3_start = time.time()
            yield f"data: {json.dumps({'type': 'stage3_start', 'data': {'timestamp': stage3_start}})}\n\n"
            stage3_result = await stage3_synthesize_final(augmented_content, stage1_results, stage2_results, dispatch_plan=dispatch_plan, conversation_history=history)

            stage3_tokens = stage3_result.get("tokens", {}).get("total_tokens", 0)
            total_tokens += stage3_tokens
            stage3_duration = round(time.time() - stage3_start, 2)

            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result, 'timing': {'duration_sec': stage3_duration, 'tokens': stage3_tokens}})}\n\n"

            # ─── Final usage update with actual token count ────────────────
            final_usage = storage.increment_usage(tokens=total_tokens)
            # Decrement count by 1 since we already incremented earlier
            final_usage["used"] -= 1

            overall_duration = round(time.time() - overall_start, 2)

            yield f"data: {json.dumps({'type': 'usage_update', 'data': final_usage})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event with total timing
            yield f"data: {json.dumps({'type': 'complete', 'data': {'total_duration_sec': overall_duration, 'total_tokens': total_tokens}})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

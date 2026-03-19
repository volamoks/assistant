"""
Plaud transcript analysis using Groq LLM API.
Handles chunking and retry logic for rate limits.
"""

import os
import time
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set")

# Configuration
MAX_CHUNK_SIZE = 40000  # Leave room for prompt overhead
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_SIZE) -> list:
    """
    Split text into chunks if it's too long.
    Tries to split at sentence boundaries.
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences (naive but effective)
    sentences = text.replace("\n", " ").split(". ")
    
    for sentence in sentences:
        # Add ". " back since we split on it
        sentence_with_period = sentence + ". "
        
        if len(current_chunk) + len(sentence_with_period) < max_chars:
            current_chunk += sentence_with_period
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence_with_period
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Edge case: single very long sentence
    if not chunks:
        # Force chunk at max_chars
        chunks = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
    
    return chunks


def _call_groq(prompt: str, system_prompt: str = None, retries: int = 5) -> str:
    """
    Call Groq API with retry logic for rate limits.
    
    Handles 429 Too Many Requests with exponential backoff.
    """
    if system_prompt is None:
        system_prompt = (
            "You are a highly efficient assistant. Respond in the same language as the transcript "
            "(Russian, Uzbek, or English). Give a concise summary and a bulleted list of tasks "
            "formatted exactly as '- [ ] Task Title: Detailed description of the task'."
        )
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    for attempt in range(retries):
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=120)
            
            if resp.status_code == 429:
                # Rate limited - get retry-after or use exponential backoff
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    wait_time = min(2 ** attempt * 2, 120)  # Cap at 2 minutes
                
                print(f"  -> Groq rate limited (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            
            if resp.status_code != 200:
                print(f"  -> Groq API error: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
            
            result = resp.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                print(f"  -> Groq request error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception("Max retries exceeded for Groq API call")


def extract_summary_and_tasks(text: str) -> str:
    """
    Use Groq Llama 3 API to summarize and extract tasks.
    Automatically chunks large transcripts and combines results.
    """
    chunks = _chunk_text(text, MAX_CHUNK_SIZE)
    
    if len(chunks) == 1:
        # Single chunk - just process directly
        prompt = (
            "Analyze the following transcript. Extract the main points and actionable tasks. "
            "If there are no tasks, just summarize.\n\n"
            f"Transcript:\n{text}"
        )
        return _call_groq(prompt)
    
    # Multiple chunks - process each and combine
    print(f"  -> Transcript too large ({len(text)} chars), splitting into {len(chunks)} chunks...")
    
    summaries = []
    for idx, chunk in enumerate(chunks):
        print(f"  -> Processing chunk {idx + 1}/{len(chunks)} ({len(chunk)} chars)...")
        
        prompt = (
            "Analyze the following transcript chunk. Extract the main points and actionable tasks. "
            "If there are no tasks, just summarize.\n\n"
            f"Transcript:\n{chunk}"
        )
        
        summary = _call_groq(prompt)
        summaries.append(summary)
    
    # Final pass to combine chunks
    combined = "\n\n".join(summaries)
    
    final_prompt = (
        "Combine these summaries into a single cohesive summary and a single consolidated task list. "
        "Group all tasks at the bottom, strictly formatted as '- [ ] Task Title: Detailed description of the task'.\n\n"
        f"Summaries:\n{combined}"
    )
    
    final_system = (
        "You are an assistant. Format the final output cleanly. Group all tasks at the bottom, "
        "strictly formatted as '- [ ] Task Title: Detailed description of the task'."
    )
    
    return _call_groq(final_prompt, system_prompt=final_system)

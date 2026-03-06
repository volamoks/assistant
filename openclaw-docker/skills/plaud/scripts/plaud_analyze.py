import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def chunk_text(text, max_chars=20000):
    """Split text into chunks if it's too long for LLM context."""
    chunks = []
    current_chunk = ""
    for sentence in text.replace("\n", " ").split(". "):
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def extract_summary_and_tasks(text):
    """Use Groq Llama 3 API to summarize and extract tasks."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    chunks = chunk_text(text)
    summaries = []
    
    for idx, chunk in enumerate(chunks):
        prompt = f"Analyze the following transcript chunk. Extract the main points and actionable tasks. If there are no tasks, just summarize.\n\nTranscript:\n{chunk}"
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a highly efficient assistant. Respond in the same language as the transcript (Russian, Uzbek, or English). Give a concise summary and a bulleted list of tasks formatted exactly as '- [ ] Task Title: Detailed description of the task'."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"Error from Groq API (LLM analysis): {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        result = resp.json()
        summaries.append(result["choices"][0]["message"]["content"])
    
    if len(summaries) == 1:
        return summaries[0]
    
    # Final pass to combine chunks if there were multiple
    combined = "\n\n".join(summaries)
    final_prompt = f"Combine these summaries into a single cohesive summary and a single consolidated task list.\n\nSummaries:\n{combined}"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are an assistant. Format the final output cleanly. Group all tasks at the bottom, strictly formatted as '- [ ] Task Title: Detailed description of the task'."},
            {"role": "user", "content": final_prompt}
        ],
        "temperature": 0.3
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"Error from Groq API (LLM analysis): {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

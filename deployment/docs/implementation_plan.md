# Master Implementation Plan: Mac Mini AI Orchestrator

## 1. System Goal
Transform the Mac Mini into an always-on "Jarvis" (`100.x.x.x` on Tailscale) that orchestrates 11 specialized AI agents to manage work, personal life, travel, and health.

## 2. Agent Architecture (The "Dream Team 2026")

| ID | Role | Model | Key Capability |
| :--- | :--- | :--- | :--- |
| **`default`** (No ID) | **Main Chat / General** | **Minimax M2.5** 👑 | **Alive & Fast**. Universal answers. |
| **`agent_router`** | **CEO / Dispatcher** | **Gemini 3 Flash** ⚡️ | **Tech Brain**. Best instruction following. |
| `agent_work` | PM Strategy | **Qwen 3.5 Plus** 🧠 | **GPT-5 Level**. Massive 397B Native Visual context. |
| **`agent_research`** | **Researcher** | **Kimi K2.5** 📚 | **Context King**. Reads books/PDFs. |
| **`agent_coder`** | **DevOps / Coder** | **Qwen 3.5 (397B)** 🛠️ | **Native MCP**. Understands entire repos. |
| **`agent_sysadmin`**| **Watchdog** | **DeepSeek V3.2** | **Monitoring**. Fixes server issues. |
| `agent_interviewer`| Bar Raiser | **Gemini 3 Deep Think** 🎓 | **Interviewer**. Mock Agoda interviews. |
| **`agent_investor`**| **CFO / Finance** | **Qwen 3 Max** 💰 | **Math/Risk**. Crypto portfolio analysis. |
| **`agent_networker`**| **PR / Community** | **Minimax M2.5** 🗣️ | **Vibe Writer**. Posts for Product Choyxona. |
| `agent_psychologist`| Therapist | **Minimax M2.5** ❤️ | **High EQ**. Emotional support. |
| `agent_chef` | Sous-Chef | **Gemini 3 Flash** 🍳 | **Vision**. Recognizes food. |
| `agent_travel` | Logistics | **Gemini 3 Flash** ✈️ | **Docs**. Scans tickets/visas. |
| `agent_transport` | Navigator | **Gemini 3 Flash** 🗺️ | **Maps**. Routes & Transport. |
| `agent_shopper` | Procurement | **DeepSeek V3.2** 🛒 | **Extraction**. Parses prices/specs. |

## 3. Workflow Logic

### A. The "Obsidian First" Principle
-   All written content (Drafts, Tickets, Ideas) goes to **Obsidian** first.
-   **Path**: `~/Documents/ObsidianVault/Inbox/`
-   **Why**: Speed, Privacy, Offline-first.
-   **Sync**: User manually pushes to Jira/Confluence when ready.

### B. API Strategy
-   **Travel**: **Amadeus API** (Free Tier: 2000 req/mo).
-   **Transport**: **Web Search** (Yandex Maps / Tashkent Transport).
-   **Shopping/Airbnb**: **Web Search**.
-   **Work**: **Jira/Confluence API Tokens**.

### C. Extended Skills Strategy
-   **Google Drive**: **Native Filesystem** (App installed on Mac).
    -   *Logic*: Agent treats GDrive as `/Users/abror/Google Drive`. Zero latency, no API limits.
-   **Presentations**: **Google Slides MCP** or **Obsidian Slides** (Markdown).
-   **Diagrams (Mermaid/Gantt)**: **Obsidian Native**.
    -   *Logic*: Agent writes Mermaid code block -> Obsidian renders Chart/Mindmap.
-   **Miro**: Future Scope (Start with Obsidian Canvas).

## 4. Hierarchy & Files

```text
~/.openclaw/
├── openclaw.json           # Main config (Router as default)
└── agents/                 # Specialized Configs
    ├── router.json
    ├── work.json
    ├── personal.json
    ├── travel.json
    ├── ... (all 11 agents)

~/.gemini/antigravity/brain/.../
├── MEMORY.md               # User Context (Projects, Bio)
├── AGENTS.md               # Registry (Router's Phonebook)
├── SOUL_ROUTER.md          # System Prompts...
├── SOUL_WORK.md
└── ...
```

## 5. Next Steps (Execution on Mac Mini)

1.  **System Prep**:
    -   Install OpenClaw, Tailscale, Obsidian.
    -   Prevent sleep (Amphetamine).

2.  **API Keys Setup**:
    -   Get **Amadeus** Key (Travel).
    -   Get **Atlassian** Token (Work).
    -   Get **Kiwi** (Optional, fallback).

3.  **Launch**:
    -   Run `openclaw --profile default`.
    -   Test: "Ticket for BNPL", "Flight to Istanbul", "Bus 67 schedule".

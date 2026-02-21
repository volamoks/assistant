# Technical Assignment (TZ): Mac Mini AI Orchestrator

## 1. Project Goal
Transform the Mac Mini into a central, always-on AI Orchestrator ("Jarvis") that manages the user's personal and professional digital life. It will unify inputs from various sources (voice, text, apps) and intelligently route them to the correct systems (Obsidian, Jira, Confluence, Calendar).

## 2. Architecture Overview

```mermaid
graph TD
    subgraph Inputs
        Plaud[Plaud Note (Voice)] -->|GDrive/Email| Watcher[File Watcher]
        TG[Telegram Bot] -->|Webhook| Gateway[OpenClaw Gateway]
        ObsidianInput[Obsidian QuickAdd] -->|HTTP| Gateway
    end

    subgraph "Mac Mini Orchestrator (OpenClaw)"
        Gateway --> Router{Router Agent}
        
        Router -->|Personal/Note| Personal[Personal Agent]
        Router -->|Work/Task| Work[Work Agent]
        Router -->|System/Control| Sys[System Agent]
    end

    subgraph Outputs
        Personal -->|Write| ObsidianVault[Obsidian (Local)]
        Personal -->|Schedule| AppleApps[Apple Reminders/Calendar]
        
        Work -->|Track| Jira[Jira Cloud]
        Work -->|Document| Confluence[Confluence Cloud]
        
        Sys -->|Control| MacOS[Mac OS Shell/AppleScript]
    end
```

## 3. Component Specifications

### 3.1. Core Orchestrator (OpenClaw)
-   **Role**: Central nervous system.
-   **Configuration**:
    -   **Profile**: `default` (run on startup via `launchd`).
    -   **Network**: Tailscale enabled (IP `100.x.x.x`) for secure remote access from iPad/iPhone.

### 3.2. Models (The Brains)
-   **Router Model (Speed)**:
    -   *Model*: `gemini-2.0-flash` or local `llama3:8b` (via Ollama).
    -   *Role*: Fast classification (<1s latency). Decides "Where does this go?".
-   **Worker Model (Intelligence)**:
    -   *Model*: `claude-3-5-sonnet` or `gpt-4o` (via OpenRouter).
    -   *Role*: Complex processing. Drafting docs, splitting tasks, formatting markdown.

### 3.3. Integration Points

#### A. Plaud Note (Voice Pipeline)
-   **Problem**: Plaud is a closed ecosystem.
-   **Solution**:
    1.  Configure Plaud to sync to **Google Drive**.
    2.  Install Google Drive for Desktop on Mac Mini.
    3.  OpenClaw **Watcher Skill** monitors the synced folder.
    4.  Action: When new `.txt` or `.md` transcript appears -> ingest -> summarize -> route.

#### B. Obsidian (The Second Brain)
-   **Input**: Use `QuickAdd` plugin in Obsidian to send HTTP POST to OpenClaw `localhost` (when on Mac) or Tailscale IP (when mobile).
-   **Output**: OpenClaw writes directly to `~/Documents/ObsidianVault/Inbox.md` using the **File System Skill**. No API needed, ultra-fast.

#### C. Work Suite (Jira / Confluence)
-   **Integration**: Custom OpenClaw Skills.
-   **Auth**: Atlassian API Token.
-   **Capabilities**:
    -   `jira.create_issue`: Create task from natural language.
    -   `confluence.create_page`: Create meeting notes from Plaud transcript.

#### D. Apple Ecosystem
-   **Skills**: `apple-reminders`, `calendar` (via ready-made OpenClaw skills).
-   **Usage**: "Remind me to call Mom at 6 PM" -> Native Apple Reminder.

## 4. Agent Implementation Details (Based on Multi-Agent Best Practices)

### 4.1. File Structure
To avoid "bloated context" and ensure specialization, we will use the following structure:
-   **`AGENTS.md` (Registry)**: Master list of all agents, their `id`, `description`, and `capabilities`. The Router uses this to decide who to call.
-   **`MEMORY.md` (Context)**: Long-term operational context (User's preferences, project abbreviations, team structure).
-   **`skills/`**: Functional tools (Jira API, File System).

### 4.2. Agent Personas (`SOUL.md` equivalent)
Each agent in OpenClaw will have a strict system prompt acting as its "SOUL":

#### A. Router (The CEO)
-   **Goal**: Route, don't solve.
-   **Context**: Minimal. Only sees `AGENTS.md` and the user's input.
-   **Output**: JSON `{ "target_agent": "work", "input": "..." }`.

#### B. Work Agent ( The Specialist)
-   **Goal**: Draft professional docs/tasks in Obsidian.
-   **Context**: Full project context, access to `obsidian` (write) and `jira`/`confluence` (read-only for context).
-   **Flow**: Write to `Obsidian/Work/Inbox.md`. User manually "pushes" to Jira later.

#### C. Personal Agent (The Executive Assistant)
-   **Goal**: Manage life.
-   **Context**: Personal preferences, access to `obsidian` and `apple` skills.

#### D. New Specialized Agents
-   **Travel**: Amadeus (Flights/Hotels). Airbnb via Web Search.
-   **Learning**: Mock interviews, explain concepts.
-   **Chef**: Recipe ideas.
-   **Shopper**: Price comparison (Amazon/Ali/Local).
-   **Lifestyle Suite**:
    -   **Psychologist**: CBT-based journaling and reflection.
    -   **Cynologist**: Dog training tips and command schedules.
    -   **Fitness**: Workout plans and nutrition tracking.
    -   **Transport**: Tashkent routes via Yandex Maps (Web Search).

## 5. Implementation Plan

### Phase 1: Foundation
1.  **System**: Ensure Mac Mini never sleeps (Amphetamine/Caffeine) and OpenClaw runs on boot.
2.  **Access**: Verify Tailscale access from all devices.
3.  **Models**: Configure `openclaw.json` with OpenRouter keys.

### Phase 2: The Router (Logic)
1.  Create `router` agent with a strict system prompt intent list:
    `WORK`, `PERSONAL`, `TRAVEL`, `LEARN`, `COOK`, `SHOP`, `HEALTH`, `PETS`, `TRANSPORT`.

### Phase 3: Integrations
1.  **Obsidian (The Hub)**: All agents write here first.
2.  **Jira/Confluence**: Write "Push to Jira" script for Obsidian.
3.  **Travel**: Register Amadeus.
4.  **Transport**: Use Web Search for "Bus 67 schedule Tashkent".

## 6. Security & Privacy
-   All personal notes remain **local** on the Mac Mini.
-   Work data is transmitted **only** to official Jira/Confluence APIs.
-   Remote access **only** via encrypted VPN (Tailscale).

---
**Approved by User:** [ ]

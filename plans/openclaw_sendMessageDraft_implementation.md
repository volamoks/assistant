# OpenClaw sendMessageDraft Implementation Plan

## Overview
Enable real-time streaming responses in OpenClaw using Telegram Bot API 9.5+'s new `sendMessageDraft` method.

## Background
- **Current situation**: OpenClaw Docker image was built Feb 22, 2026
- **API release**: `sendMessageDraft` became available to all bots on March 1, 2026 (Bot API 9.5+)
- **Current implementation**: Uses `editMessageText` for updates (works but not optimal for streaming)
- **New approach**: `sendMessageDraft` provides smooth real-time animation of growing messages

## How sendMessageDraft Works

### API Details
```
POST https://api.telegram.org/bot<token>/sendMessageDraft
```

### Parameters
- `chat_id` (required): User's ID
- `draft_id` (required): Any non-zero integer (reuse same ID for animation continuity)
- `text` (required): Current partial text (update incrementally)
- `parse_mode` (optional): Markdown or HTML
- `entities` (optional): Message entities

### Flow
1. Start streaming: Call `sendMessageDraft` with a unique `draft_id` and initial text chunk
2. Continue streaming: Call repeatedly with same `draft_id` and accumulated text
3. Finalize: Call `sendMessage` or `editMessageText` with final complete text

**Important**: Works in private chats only (one-on-one conversations).

## Implementation Steps

### Step 1: Access OpenClaw Source Code

The source code needs to be obtained and modified. Based on the container structure:
- Main entry: `/app/openclaw.mjs`
- Likely TypeScript/JavaScript source in `/app/src/`
- Telegram integration likely in `/app/src/telegram/` or `/app/src/gateway/`

**Action**: Clone or extract the openclaw source code from the container or repository.

```bash
# Option 1: Clone from GitHub (if public)
git clone https://github.com/openclaw/openclaw.git /data/bot/openclaw-source

# Option 2: Copy from running container
docker cp openclaw-latest:/app /data/bot/openclaw-source
```

### Step 2: Locate Telegram Message Sending Code

Search for existing Telegram Bot API integration:

```bash
# Find where sendMessage is called
grep -r "sendMessage" /app/src --include="*.ts" --include="*.js"
grep -r "telegram" /app/src --include="*.ts" --include="*.js" -l

# Likely locations:
# - /app/src/gateway/telegram-provider.ts
# - /app/src/telegram/bot.ts
# - /app/src/channels/telegram.ts
```

### Step 3: Implement sendMessageDraft Support

Create or modify the Telegram provider class to add streaming support.

**Example Implementation**:

```typescript
// src/gateway/telegram-provider.ts or similar

interface SendMessageDraftOptions {
  chatId: string | number;
  draftId: number;
  text: string;
  parseMode?: 'Markdown' | 'MarkdownV2' | 'HTML';
  entities?: MessageEntity[];
}

class TelegramStreamingMessenger {
  private botToken: string;
  private activeDrafts: Map<string, { draftId: number; lastText: string }> = new Map();

  constructor(botToken: string) {
    this.botToken = botToken;
  }

  /**
   * Start or update a streaming message draft
   */
  async sendDraft(options: SendMessageDraftOptions): Promise<void> {
    const url = `https://api.telegram.org/bot${this.botToken}/sendMessageDraft`;
    
    const payload = {
      chat_id: options.chatId,
      draft_id: options.draftId,
      text: options.text,
      parse_mode: options.parseMode,
      entities: options.entities
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`sendMessageDraft failed: ${error}`);
      }

      // Track this draft
      this.activeDrafts.set(String(options.chatId), {
        draftId: options.draftId,
        lastText: options.text
      });
    } catch (error) {
      console.error('Failed to send message draft:', error);
      // Fallback to regular message if draft fails
      throw error;
    }
  }

  /**
   * Finalize a streaming message by converting draft to actual message
   */
  async finalizeDraft(
    chatId: string | number,
    finalText: string,
    parseMode?: 'Markdown' | 'MarkdownV2' | 'HTML'
  ): Promise<number | null> {
    // Remove from active drafts
    this.activeDrafts.delete(String(chatId));

    // Send final message using regular sendMessage
    // This replaces the draft with the permanent message
    const url = `https://api.telegram.org/bot${this.botToken}/sendMessage`;
    
    const payload = {
      chat_id: chatId,
      text: finalText,
      parse_mode: parseMode
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    return data.ok ? data.result.message_id : null;
  }

  /**
   * Check if chat supports streaming (private chats only)
   */
  isStreamingSupported(chatType: string): boolean {
    return chatType === 'private';
  }
}
```

### Step 4: Integrate with AI Response Streaming

Modify the message handling code to use streaming for AI responses:

```typescript
// Integration in message handler

class MessageHandler {
  private messenger: TelegramStreamingMessenger;
  private draftCounter: number = 1;

  async handleStreamingResponse(
    chatId: string,
    chatType: string,
    streamGenerator: AsyncGenerator<string>
  ): Promise<void> {
    // Only use streaming for private chats
    if (!this.messenger.isStreamingSupported(chatType)) {
      // Fall back to regular message for groups/channels
      return this.handleRegularResponse(chatId, streamGenerator);
    }

    const draftId = this.draftCounter++;
    let accumulatedText = '';
    let chunkCount = 0;
    
    // Configure chunking strategy
    const MIN_CHUNK_SIZE = 50;  // Minimum chars before first update
    const UPDATE_INTERVAL = 3;  // Update every N chunks
    const MAX_CHUNK_SIZE = 4000; // Telegram message limit

    for await (const chunk of streamGenerator) {
      accumulatedText += chunk;
      chunkCount++;

      // Send draft update every N chunks or when buffer is large enough
      if (chunkCount % UPDATE_INTERVAL === 0 || accumulatedText.length >= MIN_CHUNK_SIZE) {
        // Truncate if needed (Telegram has limits)
        const draftText = accumulatedText.slice(0, MAX_CHUNK_SIZE);
        
        await this.messenger.sendDraft({
          chatId,
          draftId,
          text: draftText,
          parseMode: 'Markdown'
        });
      }
    }

    // Finalize with complete message
    await this.messenger.finalizeDraft(chatId, accumulatedText, 'Markdown');
  }
}
```

### Step 5: Add Configuration Option

Add a setting to enable/disable streaming in `openclaw.json`:

```json
{
  "gateway": {
    "mode": "local",
    "telegram": {
      "streamingEnabled": true,
      "streamingConfig": {
        "updateInterval": 3,
        "minChunkSize": 50,
        "onlyInPrivate": true
      }
    }
  }
}
```

Configuration loader update:

```typescript
// In config loading code
const streamingConfig = {
  enabled: config.gateway?.telegram?.streamingEnabled ?? true,
  updateInterval: config.gateway?.telegram?.streamingConfig?.updateInterval ?? 3,
  minChunkSize: config.gateway?.telegram?.streamingConfig?.minChunkSize ?? 50,
  onlyInPrivate: config.gateway?.telegram?.streamingConfig?.onlyInPrivate ?? true
};
```

### Step 6: Update Dockerfile

Modify `openclaw.Dockerfile` to build from the modified source:

```dockerfile
# Option 1: If building from local modified source
FROM node:20-alpine AS builder
WORKDIR /build
COPY ./openclaw-source /build
RUN npm install && npm run build

FROM ghcr.io/openclaw/openclaw:main
# ... existing setup ...
# Copy modified built files
COPY --from=builder /build/dist /app/dist
COPY --from=builder /build/openclaw.mjs /app/openclaw.mjs
```

Or if using a forked repo:

```dockerfile
FROM ghcr.io/openclaw/openclaw:main

# Switch to root for modifications
USER root

# Install git and dependencies
RUN apt-get update && apt-get install -y git

# Clone your fork with sendMessageDraft support
RUN git clone https://github.com/yourusername/openclaw-fork /tmp/openclaw-source && \
    cd /tmp/openclaw-source && \
    npm install && \
    npm run build && \
    cp -r dist/* /app/dist/ && \
    cp openclaw.mjs /app/openclaw.mjs

# Revert to unprivileged user
USER 501:20
```

### Step 7: Build and Deploy

```bash
# Build the new image
cd /data/bot/openclaw-docker
docker-compose build openclaw

# Or build manually
docker build -f openclaw.Dockerfile -t openclaw-streaming:latest .

# Update docker-compose to use new image
docker-compose up -d openclaw

# Test streaming in private chat
```

### Step 8: Testing Checklist

- [ ] Test in private chat with streaming enabled
- [ ] Test in group chat (should fallback to regular messages)
- [ ] Test with long responses (4000+ chars)
- [ ] Test with Markdown formatting
- [ ] Test error handling when draft API fails
- [ ] Verify draft is properly finalized to permanent message
- [ ] Check performance with slow AI responses
- [ ] Verify configuration toggle works

## Key Considerations

1. **Private Chats Only**: `sendMessageDraft` only works in one-on-one conversations. Must detect chat type and fallback for groups/channels.

2. **API Rate Limits**: Even though drafts animate smoothly, don't spam the API. Batch updates every 3-5 chunks or 50-100ms.

3. **Error Handling**: If `sendMessageDraft` fails (e.g., API not available in user's client), gracefully fall back to `editMessageText` or `sendMessage`.

4. **Message Length**: Telegram has a 4096 character limit. Truncate or split long messages.

5. **Concurrent Drafts**: Each chat can only have one active draft at a time. Track active drafts per chat.

6. **Finalization**: Always finalize the draft with `sendMessage` or `editMessageText` to make it permanent.

## Alternative: Minimal Patch Approach

If modifying full source is complex, create a minimal wrapper that monkey-patches the existing Telegram provider:

```typescript
// patches/telegram-streaming-patch.ts
// Load this early in openclaw.mjs

const originalSendMessage = TelegramProvider.prototype.sendMessage;

TelegramProvider.prototype.sendMessage = async function(
  chatId: string,
  text: string,
  options: any
) {
  // Check if this is a streaming context
  if (options?.streaming && this.isPrivateChat(chatId)) {
    return this.sendStreaming(chatId, text, options);
  }
  return originalSendMessage.call(this, chatId, text, options);
};
```

## Migration Path

1. **Phase 1**: Implement `sendMessageDraft` alongside existing `editMessageText` code
2. **Phase 2**: Add configuration toggle (default: disabled)
3. **Phase 3**: Test extensively in private chats
4. **Phase 4**: Enable by default for private chats only
5. **Phase 5**: Consider for groups if Telegram extends support

## Expected Benefits

- **Better UX**: Users see AI responses appearing in real-time
- **Smoother Animation**: Native Telegram animation vs manual edit updates
- **Reduced Perceived Latency**: Users see content immediately, not at the end
- **Modern Experience**: Matches other AI chat interfaces (ChatGPT, Claude, etc.)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API not supported on client | Fallback to `editMessageText` |
| Rate limiting | Batch updates, add delays |
| Long messages hitting limits | Chunking strategy |
| Groups not supported | Auto-detect chat type |
| Old clients without draft support | API gracefully degrades |

## Files to Modify

1. `src/gateway/telegram-provider.ts` - Add `sendMessageDraft` support
2. `src/gateway/message-handler.ts` - Integrate streaming for AI responses
3. `src/config/schema.ts` - Add streaming configuration options
4. `openclaw.Dockerfile` - Build from modified source
5. `docker-compose.yml` - May need to update image reference

## Success Criteria

- AI responses in private chats stream in real-time using `sendMessageDraft`
- Groups and channels continue to work with regular messages
- Configuration toggle works correctly
- No degradation in response quality or formatting
- Performance remains acceptable (no significant latency increase)

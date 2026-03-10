import {
  listProjects
} from "./chunk-AZYOKJYC.js";
import {
  DATE_HEADING_RE,
  inferObservationType,
  normalizeObservationContent,
  parseObservationLine,
  parseObservationMarkdown,
  renderObservationMarkdown,
  renderScoredObservationLine
} from "./chunk-FHFUXL6G.js";
import {
  listConfig,
  listRouteRules,
  matchRouteRule
} from "./chunk-ITPEXLHA.js";
import {
  ensureLedgerStructure,
  ensureParentDir,
  getLegacyObservationPath,
  getObservationPath,
  getRawTranscriptPath,
  toDateKey
} from "./chunk-Z2XBWN7A.js";
import {
  createBacklogItem,
  listBacklogItems,
  listTasks,
  updateBacklogItem,
  updateTask
} from "./chunk-QWQ3TIKS.js";

// src/observer/compressor.ts
var OPENAI_BASE_URL = "https://api.openai.com/v1";
var OLLAMA_BASE_URL = "http://localhost:11434/v1";
var DEFAULT_PROVIDER_MODELS = {
  anthropic: "claude-3-5-haiku-latest",
  openai: "gpt-4o-mini",
  gemini: "gemini-2.0-flash",
  "openai-compatible": "gpt-4o-mini",
  ollama: "llama3.2"
};
var CRITICAL_RE = /(?:\b(?:decision|decided|chose|chosen|selected|picked|opted|switched to)\s*:?|\bdecid(?:e|ed|ing|ion)\b|\berror\b|\bfail(?:ed|ure|ing)?\b|\bblock(?:ed|er)?\b|\bbreaking(?:\s+change)?s?\b|\bcritical\b|\b\w+\s+chosen\s+(?:for|over|as)\b|\bpublish(?:ed)?\b.*@?\d+\.\d+|\bmerge[d]?\s+(?:PR|pull\s+request)\b|\bshipped\b|\breleased?\b.*v?\d+\.\d+|\bsigned\b.*\b(?:contract|agreement|deal)\b|\bpricing\b.*\$|\bdemo\b.*\b(?:completed?|done|finished)\b|\bmeeting\b.*\b(?:completed?|done|finished)\b|\bstrategy\b.*\b(?:pivot|change|shift)\b)/i;
var DEADLINE_WITH_DATE_RE = /(?:(?:\bdeadline\b|\bdue(?:\s+date)?\b|\bcutoff\b).*(?:\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})|(?:\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}).*(?:\bdeadline\b|\bdue(?:\s+date)?\b|\bcutoff\b))/i;
var NOTABLE_RE = /\b(prefer(?:ence|s)?|likes?|dislikes?|context|pattern|architecture|approach|trade[- ]?off|milestone|stakeholder|teammate|collaborat(?:e|ed|ion)|discussion|notable|deadline|due|timeline|deploy(?:ed|ment)?|built|configured|launched|proposal|pitch|onboard(?:ed|ing)?|migrat(?:e|ed|ion)|domain|DNS|infra(?:structure)?)\b/i;
var TODO_SIGNAL_RE = /(?:\btodo:\s*|\bwe need to\b|\bdon't forget(?: to)?\b|\bremember to\b|\bmake sure to\b)/i;
var COMMITMENT_TASK_SIGNAL_RE = /\b(?:i'?ll|i will|let me|(?:i'?m\s+)?going to|plan to|should)\b/i;
var UNRESOLVED_COMMITMENT_RE = /\b(?:need to figure out|tbd|to be determined)\b/i;
var DEADLINE_SIGNAL_RE = /\b(?:by\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow)|before\s+the\s+\w+|deadline is)\b/i;
var Compressor = class {
  provider;
  model;
  baseUrl;
  apiKey;
  now;
  fetchImpl;
  constructor(options = {}) {
    this.provider = options.provider;
    this.model = options.model;
    this.baseUrl = options.baseUrl;
    this.apiKey = options.apiKey;
    this.now = options.now ?? (() => /* @__PURE__ */ new Date());
    this.fetchImpl = options.fetchImpl ?? fetch;
  }
  async compress(messages, existingObservations) {
    const cleanedMessages = messages.map((message) => message.trim()).filter(Boolean);
    if (cleanedMessages.length === 0) {
      return existingObservations.trim();
    }
    const prompt = this.buildPrompt(cleanedMessages, existingObservations);
    const backend = this.resolveProvider();
    if (backend) {
      try {
        const llmOutput = backend.provider === "anthropic" ? await this.callAnthropic(prompt, backend) : backend.provider === "gemini" ? await this.callGemini(prompt, backend) : backend.provider === "openai" ? await this.callOpenAI(prompt, backend) : await this.callOpenAICompatible(prompt, backend);
        const normalized = this.normalizeLlmOutput(llmOutput);
        if (normalized) {
          return this.mergeObservations(existingObservations, normalized);
        }
      } catch {
      }
    }
    const fallback = this.fallbackCompression(cleanedMessages);
    return this.mergeObservations(existingObservations, fallback);
  }
  resolveProvider() {
    if (process.env.CLAWVAULT_NO_LLM) return null;
    if (this.provider) {
      const configured = this.resolveConfiguredProvider(this.provider);
      if (configured) {
        return configured;
      }
      return this.resolveProviderFromEnv(false);
    }
    return this.resolveProviderFromEnv(true);
  }
  resolveConfiguredProvider(provider) {
    const model = this.resolveModel(provider);
    if (provider === "anthropic") {
      const apiKey2 = this.resolveApiKey(provider);
      if (!apiKey2) {
        return null;
      }
      return {
        provider,
        model,
        apiKey: apiKey2
      };
    }
    if (provider === "gemini") {
      const apiKey2 = this.resolveApiKey(provider);
      if (!apiKey2) {
        return null;
      }
      return {
        provider,
        model,
        apiKey: apiKey2
      };
    }
    if (provider === "openai") {
      const apiKey2 = this.resolveApiKey(provider);
      if (!apiKey2) {
        return null;
      }
      return {
        provider,
        model,
        apiKey: apiKey2,
        baseUrl: this.resolveBaseUrl(provider)
      };
    }
    const apiKey = this.resolveApiKey(provider) ?? void 0;
    return {
      provider,
      model,
      apiKey,
      baseUrl: this.resolveBaseUrl(provider)
    };
  }
  resolveProviderFromEnv(allowConfiguredModel) {
    const anthropicApiKey = this.readEnvValue("ANTHROPIC_API_KEY");
    if (anthropicApiKey) {
      return {
        provider: "anthropic",
        model: allowConfiguredModel ? this.resolveModel("anthropic") : DEFAULT_PROVIDER_MODELS.anthropic,
        apiKey: anthropicApiKey
      };
    }
    const openAiApiKey = this.readEnvValue("OPENAI_API_KEY");
    if (openAiApiKey) {
      return {
        provider: "openai",
        model: allowConfiguredModel ? this.resolveModel("openai") : DEFAULT_PROVIDER_MODELS.openai,
        apiKey: openAiApiKey,
        baseUrl: OPENAI_BASE_URL
      };
    }
    const geminiApiKey = this.readEnvValue("GEMINI_API_KEY");
    if (geminiApiKey) {
      return {
        provider: "gemini",
        model: allowConfiguredModel ? this.resolveModel("gemini") : DEFAULT_PROVIDER_MODELS.gemini,
        apiKey: geminiApiKey
      };
    }
    return null;
  }
  resolveModel(provider) {
    const configuredModel = this.model?.trim();
    if (configuredModel) {
      return configuredModel;
    }
    return DEFAULT_PROVIDER_MODELS[provider];
  }
  resolveApiKey(provider) {
    const configuredApiKey = this.apiKey?.trim();
    if (configuredApiKey) {
      return configuredApiKey;
    }
    if (provider === "anthropic") {
      return this.readEnvValue("ANTHROPIC_API_KEY");
    }
    if (provider === "gemini") {
      return this.readEnvValue("GEMINI_API_KEY");
    }
    return this.readEnvValue("OPENAI_API_KEY");
  }
  resolveBaseUrl(provider) {
    const configuredBaseUrl = this.baseUrl?.trim();
    if (configuredBaseUrl) {
      return configuredBaseUrl.replace(/\/+$/, "");
    }
    if (provider === "ollama") {
      return OLLAMA_BASE_URL;
    }
    return OPENAI_BASE_URL;
  }
  readEnvValue(name) {
    const value = process.env[name]?.trim();
    return value ? value : null;
  }
  buildPrompt(messages, existingObservations) {
    return [
      "You are an observer that compresses raw AI session messages into durable, human-meaningful observations.",
      "",
      "Rules:",
      "- Output markdown only.",
      "- Group observations by date heading: ## YYYY-MM-DD",
      "- Each observation line MUST follow: - [type|c=<0.00-1.00>|i=<0.00-1.00>] <observation>",
      "- Allowed type tags: decision, preference, fact, commitment, task, todo, commitment-unresolved, milestone, lesson, relationship, project",
      "- i >= 0.80 for structural/persistent observations (major decisions, blockers, releases, commitments)",
      "- i 0.40-0.79 for potentially important observations (notable context, preferences, milestones)",
      "- i < 0.40 for contextual/routine observations",
      "- Confidence c reflects extraction certainty, not importance.",
      "- Preserve source tags when present (e.g., [main], [telegram-dm], [discord], [telegram-group]).",
      "",
      "TASK EXTRACTION (required):",
      `- Emit [todo] for explicit TODO phrasing: "TODO:", "we need to", "don't forget", "remember to", "make sure to".`,
      `- Emit [task] for commitments/action intent: "I'll", "I will", "let me", "going to", "plan to", "should".`,
      '- Emit [commitment-unresolved] for unresolved commitments/questions: "need to figure out", "TBD", "to be determined".',
      '- Deadline language ("by Friday", "before the demo", "deadline is") should increase importance and usually map to [task] unless unresolved.',
      "",
      "QUALITY FILTERS (important):",
      "- DO NOT observe: CLI errors, command failures, tool output parsing issues, retry attempts, debug logs.",
      "  These are transient noise, not memories. Only observe errors if they represent a BLOCKER or an unresolved problem.",
      '- DO NOT observe: "acknowledged the conversation", "said okay", routine confirmations.',
      '- MERGE related events into single observations. If 5 images were generated, say "Generated 5 images for X" not 5 separate lines.',
      '- MERGE retry sequences: "Tried X, failed, tried Y, succeeded" \u2192 "Resolved X using Y (after initial failure)"',
      '- Prefer OUTCOMES over PROCESSES: "Deployed v1.2 to Railway" not "Started deploy... build finished... deploy succeeded"',
      "",
      "AGENT ATTRIBUTION:",
      '- If the transcript shows multiple speakers/agents, prefix observations with who did it: "Pedro asked...", "Clawdious deployed...", "Zeca generated..."',
      "- If only one agent is acting, attribution is optional.",
      "",
      "PROJECT MILESTONES (critical \u2014 these are the most valuable observations):",
      "Projects are NOT just code. Milestones include business, strategy, client, and operational events.",
      "- Use milestone/decision/commitment types for strategic events with high importance.",
      "- Use preference/lesson/relationship/project/fact when appropriate.",
      "- Examples:",
      '  "- [decision|c=0.95|i=0.90] 14:00 Pricing decision: $33K one-time + $3K/mo for Artemisa"',
      '  "- [milestone|c=0.93|i=0.88] 14:00 Published clawvault@2.1.0 to npm"',
      '  "- [project|c=0.84|i=0.58] 14:00 Deployed pitch deck to artemisa-pitch-deck.vercel.app"',
      "- Do NOT collapse multiple milestones into one line \u2014 each matters for history.",
      "",
      "COMMITMENT FORMAT (when someone promises/agrees to something):",
      '- Prefer: "- [commitment|c=...|i=...] HH:MM [COMMITMENT] <who> committed to <what> by <when>"',
      "",
      "Keep observations concise and factual. Aim for signal, not completeness.",
      "",
      "Existing observations (may be empty):",
      existingObservations.trim() || "(none)",
      "",
      "Raw messages:",
      ...messages.map((message, index) => `[${index + 1}] ${message}`),
      "",
      "Return only the updated observation markdown."
    ].join("\n");
  }
  buildOpenAICompatibleUrl(baseUrl) {
    const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");
    return `${normalizedBaseUrl}/chat/completions`;
  }
  buildOpenAICompatibleHeaders(apiKey) {
    const headers = {
      "content-type": "application/json"
    };
    if (apiKey) {
      headers.authorization = `Bearer ${apiKey}`;
    }
    return headers;
  }
  extractOpenAIContent(content) {
    if (typeof content === "string") {
      return content.trim();
    }
    if (!Array.isArray(content)) {
      return "";
    }
    const parts = content.map((part) => {
      if (typeof part === "string") {
        return part;
      }
      if (!part || typeof part !== "object") {
        return "";
      }
      const candidate = part;
      return typeof candidate.text === "string" ? candidate.text : "";
    }).filter((part) => part.trim().length > 0);
    return parts.join("\n").trim();
  }
  async callAnthropic(prompt, backend) {
    if (!backend.apiKey) {
      return "";
    }
    const response = await this.fetchImpl("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": backend.apiKey,
        "anthropic-version": "2023-06-01"
      },
      body: JSON.stringify({
        model: backend.model,
        temperature: 0.1,
        max_tokens: 1400,
        messages: [{ role: "user", content: prompt }]
      })
    });
    if (!response.ok) {
      throw new Error(`Anthropic request failed (${response.status})`);
    }
    const payload = await response.json();
    return payload.content?.filter((part) => part.type === "text" && part.text).map((part) => part.text).join("\n").trim() ?? "";
  }
  async callOpenAI(prompt, backend) {
    return this.callOpenAICompatible(prompt, backend);
  }
  async callOpenAICompatible(prompt, backend) {
    const baseUrl = backend.baseUrl ?? this.resolveBaseUrl(backend.provider);
    const response = await this.fetchImpl(this.buildOpenAICompatibleUrl(baseUrl), {
      method: "POST",
      headers: this.buildOpenAICompatibleHeaders(backend.apiKey),
      body: JSON.stringify({
        model: backend.model,
        temperature: 0.1,
        messages: [
          { role: "system", content: "You transform session logs into concise observations." },
          { role: "user", content: prompt }
        ]
      })
    });
    if (!response.ok) {
      throw new Error(`OpenAI-compatible request failed (${response.status})`);
    }
    const payload = await response.json();
    return this.extractOpenAIContent(payload.choices?.[0]?.message?.content);
  }
  async callGemini(prompt, backend) {
    if (!backend.apiKey) {
      return "";
    }
    const model = encodeURIComponent(backend.model);
    const response = await this.fetchImpl(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${backend.apiKey}`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.1, maxOutputTokens: 1400 }
        })
      }
    );
    if (!response.ok) {
      throw new Error(`Gemini request failed (${response.status})`);
    }
    const payload = await response.json();
    return payload.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";
  }
  normalizeLlmOutput(output) {
    if (!output.trim()) {
      return "";
    }
    const cleaned = output.replace(/^```(?:markdown)?\s*/i, "").replace(/\s*```$/, "").trim();
    const lines = cleaned.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const hasObservationLine = lines.some((line) => line.startsWith("- [") || /^(?:-\s*)?(🔴|🟡|🟢)\s+/.test(line));
    if (!hasObservationLine) {
      return "";
    }
    const hasDateHeading = lines.some((line) => DATE_HEADING_RE.test(line));
    const result = hasDateHeading ? cleaned : `## ${this.formatDate(this.now())}

${cleaned}`;
    const sanitized = this.sanitizeWikiLinks(result);
    return this.enforceImportanceRules(sanitized);
  }
  /**
   * Fix wiki-link corruption from LLM compression.
   * LLMs often fuse preceding word fragments into wiki-links during rewriting:
   *   "reque[[people/pedro]]" → "[[people/pedro]]"
   *   "Linke[[agents/zeca]]" → "[[agents/zeca]]"
   *   "taske[[people/pedro]]a" → "[[people/pedro]]"
   * Also fixes trailing word fragments fused after closing brackets.
   */
  sanitizeWikiLinks(markdown) {
    let result = markdown.replace(/\w+\[\[/g, " [[");
    result = result.replace(/\]\]\w+/g, "]]");
    result = result.replace(/ {2,}/g, " ");
    return result;
  }
  enforceImportanceRules(markdown) {
    const parsed = parseObservationMarkdown(markdown);
    if (parsed.length === 0) {
      return "";
    }
    const grouped = /* @__PURE__ */ new Map();
    for (const record of parsed) {
      const adjusted = this.enforceImportanceForRecord(record);
      const bucket = grouped.get(record.date) ?? [];
      bucket.push(adjusted);
      grouped.set(record.date, bucket);
    }
    return renderObservationMarkdown(grouped);
  }
  enforceImportanceForRecord(record) {
    let importance = record.importance;
    let confidence = record.confidence;
    let type = record.type;
    const inferredTaskType = this.inferTaskType(record.content);
    if (this.isCriticalContent(record.content)) {
      importance = Math.max(importance, 0.85);
      confidence = Math.max(confidence, 0.85);
      if (type === "fact") {
        type = inferObservationType(record.content);
      }
    } else if (this.isNotableContent(record.content)) {
      importance = Math.max(importance, 0.5);
      confidence = Math.max(confidence, 0.75);
    }
    if (inferredTaskType) {
      type = type === "fact" || type === "commitment" ? inferredTaskType : type;
      importance = Math.max(importance, inferredTaskType === "commitment-unresolved" ? 0.72 : 0.65);
      confidence = Math.max(confidence, 0.8);
    }
    if (type === "decision" || type === "commitment" || type === "milestone") {
      importance = Math.max(importance, 0.6);
    }
    return {
      type,
      confidence: this.clamp01(confidence),
      importance: this.clamp01(importance),
      content: record.content
    };
  }
  fallbackCompression(messages) {
    const sections = /* @__PURE__ */ new Map();
    const seen = /* @__PURE__ */ new Set();
    for (const message of messages) {
      const normalized = this.normalizeText(message);
      if (!normalized) continue;
      const date = this.extractDate(message) ?? this.formatDate(this.now());
      const time = this.extractTime(message) ?? this.formatTime(this.now());
      const line = `${time} ${normalized}`;
      const type = inferObservationType(line);
      const importance = this.inferImportance(line, type);
      const confidence = this.inferConfidence(line, type, importance);
      const dedupeKey = `${date}|${type}|${normalizeObservationContent(line)}`;
      if (seen.has(dedupeKey)) continue;
      seen.add(dedupeKey);
      const bucket = sections.get(date) ?? [];
      bucket.push({ type, confidence, importance, content: line });
      sections.set(date, bucket);
    }
    if (sections.size === 0) {
      const date = this.formatDate(this.now());
      sections.set(date, [{
        type: "fact",
        confidence: 0.7,
        importance: 0.2,
        content: `${this.formatTime(this.now())} Processed session updates.`
      }]);
    }
    return this.renderSections(sections);
  }
  mergeObservations(existing, incoming) {
    const existingRecords = parseObservationMarkdown(existing);
    const incomingRecords = parseObservationMarkdown(incoming);
    if (incomingRecords.length === 0) {
      return existing.trim();
    }
    const merged = /* @__PURE__ */ new Map();
    for (const record of existingRecords) {
      this.mergeRecord(merged, {
        date: record.date,
        type: record.type,
        confidence: record.confidence,
        importance: record.importance,
        content: record.content
      });
    }
    for (const record of incomingRecords) {
      this.mergeRecord(merged, {
        date: record.date,
        type: record.type,
        confidence: record.confidence,
        importance: record.importance,
        content: record.content
      });
    }
    return this.renderSections(merged);
  }
  mergeRecord(sections, input) {
    const bucket = sections.get(input.date) ?? [];
    const key = normalizeObservationContent(input.content);
    const index = bucket.findIndex((line) => normalizeObservationContent(line.content) === key);
    if (index === -1) {
      bucket.push({
        type: input.type,
        confidence: this.clamp01(input.confidence),
        importance: this.clamp01(input.importance),
        content: input.content.trim()
      });
      sections.set(input.date, bucket);
      return;
    }
    const existing = bucket[index];
    bucket[index] = {
      type: input.importance >= existing.importance ? input.type : existing.type,
      confidence: this.clamp01(Math.max(existing.confidence, input.confidence)),
      importance: this.clamp01(Math.max(existing.importance, input.importance)),
      content: existing.content.length >= input.content.length ? existing.content : input.content
    };
    sections.set(input.date, bucket);
  }
  renderSections(sections) {
    return renderObservationMarkdown(sections);
  }
  inferImportance(text, type) {
    const inferredTaskType = this.inferTaskType(text);
    if (this.isCriticalContent(text)) return 0.9;
    if (inferredTaskType === "commitment-unresolved") return 0.72;
    if (inferredTaskType === "task" || inferredTaskType === "todo") return 0.65;
    if (this.isNotableContent(text)) return 0.6;
    if (type === "decision" || type === "commitment" || type === "milestone") return 0.55;
    if (type === "preference" || type === "lesson" || type === "relationship" || type === "project") return 0.45;
    return 0.2;
  }
  inferConfidence(text, type, importance) {
    const inferredTaskType = this.inferTaskType(text);
    let confidence = 0.72;
    if (importance >= 0.8) confidence += 0.12;
    if (type === "decision" || type === "commitment" || type === "milestone") confidence += 0.06;
    if (inferredTaskType) confidence += 0.06;
    if (/\b(?:decided|chose|committed|deadline|released|merged)\b/i.test(text)) {
      confidence += 0.05;
    }
    return this.clamp01(confidence);
  }
  isCriticalContent(text) {
    return CRITICAL_RE.test(text) || DEADLINE_WITH_DATE_RE.test(text);
  }
  isNotableContent(text) {
    return NOTABLE_RE.test(text);
  }
  inferTaskType(text) {
    if (UNRESOLVED_COMMITMENT_RE.test(text)) {
      return "commitment-unresolved";
    }
    if (TODO_SIGNAL_RE.test(text)) {
      return "todo";
    }
    if (COMMITMENT_TASK_SIGNAL_RE.test(text) || DEADLINE_SIGNAL_RE.test(text)) {
      return "task";
    }
    return null;
  }
  normalizeText(text) {
    return text.replace(/\s+/g, " ").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").trim().slice(0, 280);
  }
  extractDate(text) {
    const match = text.match(/\b(\d{4}-\d{2}-\d{2})\b/);
    return match?.[1] ?? null;
  }
  extractTime(text) {
    const match = text.match(/\b([01]\d|2[0-3]):([0-5]\d)\b/);
    if (!match) {
      return null;
    }
    return `${match[1]}:${match[2]}`;
  }
  formatDate(date) {
    return date.toISOString().split("T")[0];
  }
  formatTime(date) {
    return date.toISOString().slice(11, 16);
  }
  clamp01(value) {
    if (!Number.isFinite(value)) return 0;
    if (value < 0) return 0;
    if (value > 1) return 1;
    return value;
  }
};

// src/observer/reflector.ts
var DATE_HEADING_RE2 = /^##\s+(\d{4}-\d{2}-\d{2})\s*$/;
var OBSERVATION_LINE_RE = /^(🔴|🟡|🟢)\s+(.+)$/u;
var Reflector = class {
  now;
  constructor(options = {}) {
    this.now = options.now ?? (() => /* @__PURE__ */ new Date());
  }
  reflect(observations) {
    const sections = this.parseSections(observations);
    if (sections.size === 0) {
      return observations.trim();
    }
    const cutoff = this.buildCutoffDate();
    const dedupeKeys = [];
    const reflected = /* @__PURE__ */ new Map();
    const dates = [...sections.keys()].sort((a, b) => b.localeCompare(a));
    for (const date of dates) {
      const sectionDate = this.parseDate(date);
      const olderThanCutoff = sectionDate ? sectionDate.getTime() < cutoff.getTime() : false;
      const lines = sections.get(date) ?? [];
      const kept = [];
      for (const line of lines) {
        if (line.priority === "\u{1F534}") {
          kept.push(line);
          continue;
        }
        if (line.priority === "\u{1F7E2}" && olderThanCutoff) {
          continue;
        }
        const key = this.normalizeText(line.content);
        const isDuplicate = dedupeKeys.some((existing) => this.isSimilar(existing, key));
        if (isDuplicate) {
          continue;
        }
        dedupeKeys.push(key);
        kept.push(line);
      }
      if (kept.length > 0) {
        reflected.set(date, kept);
      }
    }
    return this.renderSections(reflected);
  }
  buildCutoffDate() {
    const cutoff = new Date(this.now());
    cutoff.setHours(0, 0, 0, 0);
    cutoff.setDate(cutoff.getDate() - 7);
    return cutoff;
  }
  parseDate(date) {
    const parsed = /* @__PURE__ */ new Date(`${date}T00:00:00.000Z`);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return parsed;
  }
  parseSections(markdown) {
    const sections = /* @__PURE__ */ new Map();
    let currentDate = null;
    for (const rawLine of markdown.split(/\r?\n/)) {
      const dateMatch = rawLine.match(DATE_HEADING_RE2);
      if (dateMatch) {
        currentDate = dateMatch[1];
        if (!sections.has(currentDate)) {
          sections.set(currentDate, []);
        }
        continue;
      }
      if (!currentDate) continue;
      const lineMatch = rawLine.match(OBSERVATION_LINE_RE);
      if (!lineMatch) continue;
      const bucket = sections.get(currentDate) ?? [];
      bucket.push({
        priority: lineMatch[1],
        content: lineMatch[2].trim()
      });
      sections.set(currentDate, bucket);
    }
    return sections;
  }
  renderSections(sections) {
    const chunks = [];
    const dates = [...sections.keys()].sort((a, b) => a.localeCompare(b));
    for (const date of dates) {
      const lines = sections.get(date) ?? [];
      if (lines.length === 0) continue;
      chunks.push(`## ${date}`);
      chunks.push("");
      for (const line of lines) {
        chunks.push(`${line.priority} ${line.content}`);
      }
      chunks.push("");
    }
    return chunks.join("\n").trim();
  }
  normalizeText(text) {
    return text.toLowerCase().replace(/\s+/g, " ").replace(/[^\w\s:.-]/g, "").trim();
  }
  isSimilar(a, b) {
    if (a === b) return true;
    if (a.length >= 24 && (a.includes(b) || b.includes(a))) {
      return true;
    }
    return false;
  }
};

// src/observer/observer.ts
import * as fs2 from "fs";
import * as path2 from "path";

// src/observer/router.ts
import * as fs from "fs";
import * as path from "path";
var CATEGORY_PATTERNS = [
  {
    category: "decisions",
    patterns: [
      /\b(decid(?:e|ed|ing|ion)|chose|picked|went with|selected|opted)\b/i,
      /\b(decision|trade[- ]?off|alternative|rationale)\b/i
    ]
  },
  {
    category: "lessons",
    patterns: [
      /\b(learn(?:ed|ing|t)|lesson|mistake|insight|realized|discovered)\b/i,
      /\b(note to self|remember|important|don'?t forget|never again)\b/i
    ]
  },
  {
    category: "people",
    patterns: [
      /\b(said|asked|told|mentioned|emailed|called|messaged|met with)\b/i,
      /\b(client|partner|team|colleague|contact)\b/i,
      /\b(?:Pedro|Justin|Maria|Sarah|[A-Z][a-z]+ (?:said|asked|told|mentioned))\b/,
      /\b(?:talked to|met with|spoke with|chatted with|discussed with)\s+[A-Z][a-z]+\b/i,
      /\b[A-Z][a-z]+\s+(?:from|at)\s+[A-Z]/,
      /\b[A-Z][a-z]+\s+from\b/
    ]
  },
  {
    category: "preferences",
    patterns: [
      /\b(prefer(?:s|red|ence)?|like(?:s|d)?|want(?:s|ed)?|style|convention)\b/i,
      /\b(always use|never use|default to)\b/i
    ]
  },
  {
    category: "commitments",
    patterns: [
      /\b(promised|committed|deadline|due|scheduled|will do|agreed to)\b/i,
      /\b(todo|task|action item|follow[- ]?up)\b/i
    ]
  },
  {
    category: "projects",
    patterns: [
      /\b(deployed|shipped|launched|released|merged|built|created)\b/i,
      /\b(project|repo|service|api|feature|bug fix)\b/i
    ]
  }
];
var TYPE_TO_CATEGORY = {
  decision: "decisions",
  preference: "preferences",
  fact: "facts",
  commitment: "commitments",
  task: "commitments",
  todo: "commitments",
  "commitment-unresolved": "commitments",
  milestone: "projects",
  lesson: "lessons",
  relationship: "people",
  project: "projects"
};
var PAST_TENSE_TASK_HINT_RE = /\b(completed|shipped|deployed|fixed|merged|finished|resolved|closed)\b/i;
var FUTURE_TASK_HINT_RE = /\b(need to|should|todo|must|plan to)\b/i;
var Router = class {
  vaultPath;
  extractTasks;
  now;
  customRoutes;
  constructor(vaultPath, options = {}) {
    this.vaultPath = path.resolve(vaultPath);
    this.extractTasks = options.extractTasks ?? true;
    this.now = options.now ?? (() => /* @__PURE__ */ new Date());
    this.customRoutes = this.loadCustomRoutes();
  }
  /**
   * Takes observation markdown and routes items to appropriate vault categories.
   * Routes only items with importance >= 0.4.
   * Returns a summary of what was routed where.
   */
  route(observationMarkdown, context = {}) {
    this.customRoutes = this.loadCustomRoutes();
    const items = this.parseObservations(observationMarkdown);
    const routed = [];
    const knownWorkItems = this.extractTasks ? this.loadExistingWorkItems() : [];
    const knownProjectDefinitions = this.loadKnownProjectDefinitions();
    let dedupHits = 0;
    for (const item of items) {
      if (item.importance < 0.4) continue;
      if (this.extractTasks && this.isTaskObservation(item.type)) {
        const taskResult = this.routeTaskObservation(item, context, knownWorkItems);
        if (taskResult.routedItem) {
          routed.push(taskResult.routedItem);
        }
        if (taskResult.dedupHit) {
          dedupHits += 1;
        }
        continue;
      }
      const category = this.categorize(item.type, item.content);
      if (!category) continue;
      const routedItem = {
        category,
        title: item.title,
        content: item.content,
        type: item.type,
        confidence: item.confidence,
        importance: item.importance,
        date: item.date
      };
      routed.push(routedItem);
      this.appendToCategory(category, routedItem, knownProjectDefinitions);
    }
    const summary = this.buildSummary(routed, dedupHits);
    return { routed, summary };
  }
  isTaskObservation(type) {
    return type === "task" || type === "todo" || type === "commitment-unresolved";
  }
  routeTaskObservation(item, context, knownWorkItems) {
    if (this.shouldSkipCompletedTaskCandidate(item.content)) {
      console.log("[observer] skipped likely-completed task candidate");
      return { routedItem: null, dedupHit: false };
    }
    const title = this.deriveTaskTitle(item.content, item.type);
    if (!title) {
      return { routedItem: null, dedupHit: false };
    }
    const duplicate = this.findDuplicateWorkItem(title, knownWorkItems);
    if (duplicate) {
      if (item.type === "commitment-unresolved" && this.isOpenWorkItem(duplicate)) {
        this.touchExistingWorkItem(duplicate);
      }
      console.log(`[observer] dedup hit for task candidate: "${title}"`);
      return { routedItem: null, dedupHit: true };
    }
    const tags = this.mergeTags(
      ["open", "observer"],
      item.type === "task" ? ["task"] : [],
      item.type === "todo" ? ["todo"] : [],
      item.type === "commitment-unresolved" ? ["commitment"] : []
    );
    const content = this.buildTaskContextContent(item, context);
    let backlogItem;
    try {
      backlogItem = createBacklogItem(this.vaultPath, title, {
        source: "observer",
        content,
        tags
      });
    } catch (error) {
      if (error instanceof Error && /already exists/i.test(error.message)) {
        console.log(`[observer] dedup hit for task candidate: "${title}"`);
        return { routedItem: null, dedupHit: true };
      }
      throw error;
    }
    knownWorkItems.push({
      kind: "backlog",
      slug: backlogItem.slug,
      title: backlogItem.title,
      status: "open",
      source: backlogItem.frontmatter.source,
      tags: backlogItem.frontmatter.tags ?? []
    });
    return {
      dedupHit: false,
      routedItem: {
        category: "backlog",
        title: backlogItem.title,
        content: item.content,
        type: item.type,
        confidence: item.confidence,
        importance: item.importance,
        date: item.date
      }
    };
  }
  loadExistingWorkItems() {
    const taskItems = listTasks(this.vaultPath).map((task) => ({
      kind: "task",
      slug: task.slug,
      title: task.title,
      status: task.frontmatter.status,
      source: task.frontmatter.source,
      tags: task.frontmatter.tags ?? []
    }));
    const backlogItems = listBacklogItems(this.vaultPath).map((item) => ({
      kind: "backlog",
      slug: item.slug,
      title: item.title,
      status: item.frontmatter.tags?.includes("done") ? "done" : "open",
      source: item.frontmatter.source,
      tags: item.frontmatter.tags ?? []
    }));
    return [...taskItems, ...backlogItems];
  }
  findDuplicateWorkItem(title, knownWorkItems) {
    const normalizedTitle = this.normalizeTaskTitle(title);
    if (!normalizedTitle) {
      return null;
    }
    for (const item of knownWorkItems) {
      const normalizedExisting = this.normalizeTaskTitle(item.title);
      if (!normalizedExisting) {
        continue;
      }
      if (normalizedExisting === normalizedTitle) {
        return item;
      }
      if (this.jaccardWordSimilarity(normalizedTitle, normalizedExisting) > 0.8) {
        return item;
      }
    }
    return null;
  }
  normalizeTaskTitle(title) {
    return title.toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim().slice(0, 50);
  }
  jaccardWordSimilarity(a, b) {
    const aWords = new Set(a.split(" ").filter(Boolean));
    const bWords = new Set(b.split(" ").filter(Boolean));
    if (aWords.size === 0 || bWords.size === 0) {
      return 0;
    }
    let intersection = 0;
    for (const word of aWords) {
      if (bWords.has(word)) {
        intersection += 1;
      }
    }
    const unionSize = aWords.size + bWords.size - intersection;
    return unionSize === 0 ? 0 : intersection / unionSize;
  }
  deriveTaskTitle(content, type) {
    let title = content.replace(/^\d{2}:\d{2}\s+/, "").replace(/\[[^\]]+\]\s*/g, "").trim();
    if (type === "todo") {
      title = title.replace(
        /^(?:todo:\s*|we need to\s+|don't forget(?: to)?\s+|remember to\s+|make sure to\s+)/i,
        ""
      );
    } else if (type === "task") {
      title = title.replace(
        /^(?:i'?ll\s+|i will\s+|let me\s+|(?:i'?m\s+)?going to\s+|plan to\s+|should\s+)/i,
        ""
      );
    } else if (type === "commitment-unresolved") {
      title = title.replace(/^(?:need to figure out\s+|tbd[:\s-]*|to be determined[:\s-]*)/i, "");
    }
    title = title.replace(/\s+/g, " ").replace(/^[^a-zA-Z0-9]+/, "").replace(/[.?!:;,]+$/, "").trim();
    return title.slice(0, 120);
  }
  shouldSkipCompletedTaskCandidate(content) {
    if (!PAST_TENSE_TASK_HINT_RE.test(content)) {
      return false;
    }
    return !FUTURE_TASK_HINT_RE.test(content);
  }
  buildTaskContextContent(item, context) {
    const lines = ["Auto-extracted by observer from session transcript."];
    if (context.sessionKey) {
      lines.push(`Session: ${context.sessionKey}`);
    }
    if (context.transcriptId) {
      lines.push(`Transcript: ${context.transcriptId}`);
    }
    if (context.source) {
      lines.push(`Source: ${context.source}`);
    }
    const approximateTimestamp = this.extractApproximateTimestamp(item.date, item.content, context.timestamp);
    lines.push(`Approximate timestamp: ${approximateTimestamp}`);
    lines.push(`Observation type: ${item.type}`);
    lines.push(`Original observation: ${item.content}`);
    return lines.join("\n");
  }
  extractApproximateTimestamp(date, content, timestamp) {
    if (timestamp) {
      return timestamp.toISOString();
    }
    const timeMatch = content.match(/\b([01]\d|2[0-3]):([0-5]\d)\b/);
    if (timeMatch) {
      return `${date} ${timeMatch[0]}`;
    }
    return date;
  }
  isOpenWorkItem(item) {
    if (item.kind === "task") {
      return item.status !== "done";
    }
    return item.status !== "done";
  }
  touchExistingWorkItem(item) {
    if (item.kind === "task") {
      if (!this.isOpenWorkItem(item)) {
        return;
      }
      updateTask(this.vaultPath, item.slug, {});
      return;
    }
    const nextTags = this.mergeTags(item.tags, ["commitment"]);
    updateBacklogItem(this.vaultPath, item.slug, {
      source: item.source ?? "observer",
      tags: nextTags,
      lastSeen: this.now().toISOString()
    });
    item.tags = nextTags;
  }
  mergeTags(...groups) {
    const merged = /* @__PURE__ */ new Set();
    for (const group of groups) {
      for (const tag of group) {
        const normalized = tag.trim().toLowerCase();
        if (normalized) {
          merged.add(normalized);
        }
      }
    }
    return [...merged];
  }
  parseObservations(markdown) {
    const records = parseObservationMarkdown(markdown);
    return records.map((record) => ({
      type: record.type,
      confidence: record.confidence,
      importance: record.importance,
      content: record.content,
      date: record.date,
      title: record.content.slice(0, 80).replace(/[^a-zA-Z0-9\s-]/g, "").trim()
    }));
  }
  categorize(type, content) {
    const typedCategory = TYPE_TO_CATEGORY[type];
    if (typedCategory) {
      return typedCategory;
    }
    for (const { category, patterns } of CATEGORY_PATTERNS) {
      if (patterns.some((p) => p.test(content))) {
        return category;
      }
    }
    return null;
  }
  normalizeForDedup(content) {
    return normalizeObservationContent(
      content.replace(/\[\[[^\]]*\]\]/g, (match) => match.replace(/\[\[|\]\]/g, ""))
    );
  }
  /**
   * Extract entity slug from observation content for people/projects routing.
   * Returns null if no entity can be identified.
   */
  extractEntitySlug(content, category) {
    if (category !== "people" && category !== "projects") return null;
    if (category === "people") {
      const patterns = [
        /(?:talked to|met with|spoke with|chatted with|discussed with|emailed|called|messaged)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/,
        /([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|asked|told|mentioned|from|at)\b/,
        /\b(?:client|partner|colleague|contact)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/i
      ];
      for (const pattern of patterns) {
        const match = content.match(pattern);
        if (match?.[1]) return this.toSlug(match[1]);
      }
    }
    if (category === "projects") {
      const patterns = [
        /(?:deployed|shipped|launched|released|built|created|working on)\s+([A-Z][a-zA-Z0-9-]+)/,
        /"([^"]+)"\s+(?:project|repo|service)/i
      ];
      for (const pattern of patterns) {
        const match = content.match(pattern);
        if (match?.[1]) return this.toSlug(match[1]);
      }
    }
    return null;
  }
  toSlug(name) {
    return name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  }
  normalizeProjectReference(value) {
    return value.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "").trim();
  }
  escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
  extractWikiTargets(content) {
    const targets = [];
    for (const match of content.matchAll(/\[\[([^\]]+)\]\]/g)) {
      const candidate = match[1];
      if (!candidate) continue;
      const target = candidate.split("|")[0].split("#")[0].trim();
      if (target) targets.push(target);
    }
    return targets;
  }
  loadKnownProjectDefinitions() {
    try {
      return listProjects(this.vaultPath).map((project) => ({
        slug: project.slug,
        normalizedSlug: this.normalizeProjectReference(project.slug),
        title: project.title,
        normalizedTitle: project.title.toLowerCase()
      }));
    } catch {
      return [];
    }
  }
  matchKnownProjectSlug(content, knownProjects) {
    if (knownProjects.length === 0) {
      return null;
    }
    const normalizedContent = content.toLowerCase();
    const wikiTargets = this.extractWikiTargets(content).map((target) => this.normalizeProjectReference(target));
    for (const project of knownProjects) {
      if (wikiTargets.includes(project.normalizedSlug)) {
        return project.slug;
      }
      if (project.normalizedTitle && normalizedContent.includes(project.normalizedTitle)) {
        return project.slug;
      }
      const slugPattern = new RegExp(`\\b${this.escapeRegExp(project.normalizedSlug)}\\b`, "i");
      if (slugPattern.test(content)) {
        return project.slug;
      }
    }
    return null;
  }
  loadCustomRoutes() {
    try {
      return listRouteRules(this.vaultPath);
    } catch {
      return [];
    }
  }
  resolveCustomEntityPath(content, category) {
    if (category !== "people" && category !== "projects" || this.customRoutes.length === 0) {
      return null;
    }
    const matchedRule = matchRouteRule(content, this.customRoutes);
    if (!matchedRule) {
      return null;
    }
    const targetParts = matchedRule.target.split("/").map((segment) => segment.trim()).filter(Boolean);
    if (targetParts.length < 2 || targetParts[0] !== category) {
      return null;
    }
    return targetParts.slice(1).join("/");
  }
  /**
   * Resolve the file path for a routed item.
   * For people/projects: entity-slug subfolder with date file (e.g., people/pedro/2026-02-12.md)
   * For other categories: category/date.md
   */
  resolveFilePath(category, item, knownProjectDefinitions) {
    const customEntityPath = this.resolveCustomEntityPath(item.content, category);
    if (customEntityPath) {
      const customEntityDir = path.join(this.vaultPath, category, customEntityPath);
      fs.mkdirSync(customEntityDir, { recursive: true });
      return {
        filePath: path.join(customEntityDir, `${item.date}.md`),
        headerLabel: `${category}/${customEntityPath}`
      };
    }
    if (category === "projects") {
      const matchedProjectSlug = this.matchKnownProjectSlug(item.content, knownProjectDefinitions);
      if (matchedProjectSlug) {
        const projectDir = path.join(this.vaultPath, category, matchedProjectSlug);
        fs.mkdirSync(projectDir, { recursive: true });
        return {
          filePath: path.join(projectDir, `${item.date}.md`),
          headerLabel: `${category}/${matchedProjectSlug}`
        };
      }
    } else {
      const entitySlug = this.extractEntitySlug(item.content, category);
      if (entitySlug) {
        const entityDir = path.join(this.vaultPath, category, entitySlug);
        fs.mkdirSync(entityDir, { recursive: true });
        return {
          filePath: path.join(entityDir, `${item.date}.md`),
          headerLabel: `${category}/${entitySlug}`
        };
      }
    }
    const categoryDir = path.join(this.vaultPath, category);
    fs.mkdirSync(categoryDir, { recursive: true });
    return {
      filePath: path.join(categoryDir, `${item.date}.md`),
      headerLabel: category
    };
  }
  appendToCategory(category, item, knownProjectDefinitions) {
    const destination = this.resolveFilePath(category, item, knownProjectDefinitions);
    const filePath = destination.filePath;
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const existing = fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf-8").trim() : "";
    const normalizedNew = this.normalizeForDedup(item.content);
    const existingLines = existing.split(/\r?\n/);
    for (const line of existingLines) {
      const lineContent = line.replace(/^-\s*/, "").trim();
      const parsed = parseObservationLine(lineContent, item.date);
      const candidate = parsed ? parsed.content : lineContent;
      if (this.normalizeForDedup(candidate) === normalizedNew) return;
    }
    for (const line of existingLines) {
      const lineContent = line.replace(/^-\s*/, "").trim();
      const parsed = parseObservationLine(lineContent, item.date);
      const normalizedExisting = this.normalizeForDedup(parsed ? parsed.content : lineContent);
      if (normalizedExisting.length > 10 && normalizedNew.length > 10) {
        const shorter = normalizedNew.length < normalizedExisting.length ? normalizedNew : normalizedExisting;
        const longer = normalizedNew.length >= normalizedExisting.length ? normalizedNew : normalizedExisting;
        if (longer.includes(shorter) || this.similarity(normalizedNew, normalizedExisting) > 0.8) return;
      }
    }
    const linkedContent = this.addWikiLinks(item.content);
    const entry = renderScoredObservationLine({
      type: item.type,
      confidence: item.confidence,
      importance: item.importance,
      content: linkedContent
    });
    const headerLabel = destination.headerLabel;
    const header = existing ? "" : `# ${headerLabel} \u2014 ${item.date}
`;
    const newContent = existing ? `${existing}
${entry}
` : `${header}
${entry}
`;
    fs.writeFileSync(filePath, newContent, "utf-8");
  }
  /**
   * Auto-link proper nouns and known entities with [[wiki-links]].
   * Scans for capitalized names, project names, and tool names.
   * Skips content already inside [[brackets]].
   */
  addWikiLinks(content) {
    if (content.includes("[[")) return content;
    const namePattern = /\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b/g;
    const skipWords = /* @__PURE__ */ new Set([
      "The",
      "This",
      "That",
      "These",
      "Those",
      "There",
      "Then",
      "Than",
      "When",
      "Where",
      "What",
      "Which",
      "While",
      "With",
      "Would",
      "Will",
      "Should",
      "Could",
      "About",
      "After",
      "Before",
      "Between",
      "Because",
      "Also",
      "Always",
      "Already",
      "Another",
      "Any",
      "Each",
      "Every",
      "From",
      "Have",
      "Has",
      "Had",
      "Into",
      "Just",
      "Keep",
      "Like",
      "Made",
      "Make",
      "Many",
      "More",
      "Most",
      "Much",
      "Must",
      "Need",
      "Never",
      "Next",
      "None",
      "Not",
      "Now",
      "Only",
      "Other",
      "Over",
      "Same",
      "Some",
      "Such",
      "Sure",
      "Take",
      "Them",
      "They",
      "Too",
      "Under",
      "Until",
      "Upon",
      "Very",
      "Want",
      "Were",
      "Work",
      "Yet",
      "Decision",
      "Error",
      "Deadline",
      "Friday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Saturday",
      "Sunday",
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
      "Today",
      "Tomorrow",
      "Yesterday",
      "Message",
      "Feature",
      "Session",
      "Update",
      "System",
      "User",
      "Processed",
      "Working",
      "Built",
      "Deployed",
      "Discussed",
      "Talked",
      "Mentioned",
      "Requested",
      "Asked",
      "Said"
    ]);
    const knownEntities = /* @__PURE__ */ new Set([
      "PostgreSQL",
      "MongoDB",
      "Railway",
      "Vercel",
      "React",
      "Vue",
      "Svelte",
      "Express",
      "NestJS",
      "Prisma",
      "Docker",
      "Kubernetes",
      "Redis",
      "GraphQL",
      "Stripe",
      "ClawVault",
      "OpenClaw",
      "GitHub",
      "Obsidian"
    ]);
    return content.replace(namePattern, (match) => {
      if (skipWords.has(match)) return match;
      if (knownEntities.has(match)) return `[[${match}]]`;
      if (/^[A-Z][a-z]+$/.test(match) && match.length >= 3) {
        return `[[${match}]]`;
      }
      if (/^[A-Z][a-z]+ [A-Z][a-z]+$/.test(match)) {
        return `[[${match}]]`;
      }
      return match;
    });
  }
  /**
   * Jaccard similarity on word bigrams — cheap approximation.
   */
  similarity(a, b) {
    const bigrams = (s) => {
      const words = s.split(" ");
      const bg = /* @__PURE__ */ new Set();
      for (let i = 0; i < words.length - 1; i++) bg.add(`${words[i]} ${words[i + 1]}`);
      return bg;
    };
    const setA = bigrams(a);
    const setB = bigrams(b);
    if (setA.size === 0 || setB.size === 0) return 0;
    let intersection = 0;
    for (const bg of setA) if (setB.has(bg)) intersection++;
    return intersection / (setA.size + setB.size - intersection);
  }
  buildSummary(routed, dedupHits) {
    if (routed.length === 0) {
      if (dedupHits > 0) {
        return `No items routed to vault categories (dedup hits: ${dedupHits}).`;
      }
      return "No items routed to vault categories.";
    }
    const byCat = /* @__PURE__ */ new Map();
    for (const item of routed) {
      byCat.set(item.category, (byCat.get(item.category) ?? 0) + 1);
    }
    const parts = [...byCat.entries()].map(([cat, count]) => `${cat}: ${count}`);
    const suffix = dedupHits > 0 ? ` (dedup hits: ${dedupHits})` : "";
    return `Routed ${routed.length} observations \u2192 ${parts.join(", ")}${suffix}`;
  }
};

// src/observer/observer.ts
var COMPRESSION_PROVIDERS = /* @__PURE__ */ new Set([
  "anthropic",
  "openai",
  "gemini",
  "openai-compatible",
  "ollama"
]);
function asRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value;
}
function asNonEmptyString(value) {
  if (typeof value !== "string") {
    return void 0;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : void 0;
}
function asCompressionProvider(value) {
  if (typeof value !== "string") {
    return void 0;
  }
  const normalized = value.trim();
  return COMPRESSION_PROVIDERS.has(normalized) ? normalized : void 0;
}
function readCompressionConfig(vaultPath) {
  try {
    const config = listConfig(vaultPath);
    const root = asRecord(config);
    const observer = asRecord(root?.observer);
    const compression = asRecord(observer?.compression);
    if (!compression) {
      return {};
    }
    return {
      provider: asCompressionProvider(compression.provider),
      model: asNonEmptyString(compression.model),
      baseUrl: asNonEmptyString(compression.baseUrl),
      apiKey: asNonEmptyString(compression.apiKey)
    };
  } catch {
    return {};
  }
}
var Observer = class {
  vaultPath;
  tokenThreshold;
  // Kept for backwards API compatibility with callers that still pass this.
  // Reflection now runs explicitly via clawvault reflect.
  reflectThreshold;
  compressor;
  reflector;
  now;
  rawCapture;
  router;
  pendingMessages = [];
  pendingRouteContext = {};
  observationsCache = "";
  lastRoutingSummary = "";
  constructor(vaultPath, options = {}) {
    this.vaultPath = path2.resolve(vaultPath);
    this.tokenThreshold = options.tokenThreshold ?? 3e4;
    this.reflectThreshold = options.reflectThreshold ?? 4e4;
    this.now = options.now ?? (() => /* @__PURE__ */ new Date());
    const compressionConfig = readCompressionConfig(this.vaultPath);
    this.compressor = options.compressor ?? new Compressor({
      provider: options.compressionProvider ?? compressionConfig.provider,
      model: options.model ?? compressionConfig.model,
      baseUrl: options.compressionBaseUrl ?? compressionConfig.baseUrl,
      apiKey: options.compressionApiKey ?? compressionConfig.apiKey,
      now: this.now
    });
    this.reflector = options.reflector ?? new Reflector({ now: this.now });
    this.rawCapture = options.rawCapture ?? true;
    this.router = new Router(vaultPath, {
      extractTasks: options.extractTasks,
      now: this.now
    });
    ensureLedgerStructure(this.vaultPath);
    this.observationsCache = this.readTodayObservations();
  }
  async processMessages(messages, options = {}) {
    const incoming = messages.map((message) => message.trim()).filter(Boolean);
    if (incoming.length === 0) {
      return;
    }
    if (this.rawCapture) {
      this.persistRawMessages(incoming, options);
    }
    this.pendingMessages.push(...incoming);
    this.pendingRouteContext = this.mergeRouteContext(this.pendingRouteContext, options);
    const buffered = this.pendingMessages.join("\n");
    if (this.estimateTokens(buffered) < this.tokenThreshold) {
      return;
    }
    const today = this.now();
    const todayPath = getObservationPath(this.vaultPath, today);
    const existingRaw = this.readObservationForDate(today);
    const existing = this.deduplicateObservationMarkdown(existingRaw);
    if (existingRaw.trim() !== existing) {
      this.writeObservationFile(todayPath, existing);
    }
    const compressedRaw = (await this.compressor.compress(this.pendingMessages, existing)).trim();
    const routeContext = this.pendingRouteContext;
    this.pendingMessages = [];
    this.pendingRouteContext = {};
    const compressed = this.deduplicateObservationMarkdown(compressedRaw);
    if (!compressed) {
      return;
    }
    this.writeObservationFile(todayPath, compressed);
    this.observationsCache = compressed;
    const { summary } = this.router.route(compressed, routeContext);
    if (summary) {
      this.lastRoutingSummary = summary;
    }
  }
  /**
   * Force-flush pending messages regardless of threshold.
   * Call this on session end to capture everything.
   */
  async flush() {
    if (this.pendingMessages.length === 0) {
      return { observations: this.observationsCache, routingSummary: this.lastRoutingSummary };
    }
    const today = this.now();
    const todayPath = getObservationPath(this.vaultPath, today);
    const existingRaw = this.readObservationForDate(today);
    const existing = this.deduplicateObservationMarkdown(existingRaw);
    if (existingRaw.trim() !== existing) {
      this.writeObservationFile(todayPath, existing);
    }
    const compressedRaw = (await this.compressor.compress(this.pendingMessages, existing)).trim();
    const routeContext = this.pendingRouteContext;
    this.pendingMessages = [];
    this.pendingRouteContext = {};
    const compressed = this.deduplicateObservationMarkdown(compressedRaw);
    if (compressed) {
      this.writeObservationFile(todayPath, compressed);
      this.observationsCache = compressed;
      const { summary } = this.router.route(compressed, routeContext);
      this.lastRoutingSummary = summary;
    }
    return { observations: this.observationsCache, routingSummary: this.lastRoutingSummary };
  }
  getObservations() {
    this.observationsCache = this.readTodayObservations();
    return this.observationsCache;
  }
  estimateTokens(input) {
    return Math.ceil(input.length / 4);
  }
  readTodayObservations() {
    return this.readObservationForDate(this.now());
  }
  readObservationForDate(date) {
    const ledgerPath = getObservationPath(this.vaultPath, date);
    const ledgerValue = this.readObservationFile(ledgerPath);
    if (ledgerValue) {
      return ledgerValue;
    }
    return this.readObservationFile(getLegacyObservationPath(this.vaultPath, toDateKey(date)));
  }
  readObservationFile(filePath) {
    if (!fs2.existsSync(filePath)) {
      return "";
    }
    return fs2.readFileSync(filePath, "utf-8").trim();
  }
  writeObservationFile(filePath, content) {
    ensureParentDir(filePath);
    fs2.writeFileSync(filePath, `${content.trim()}
`, "utf-8");
  }
  deduplicateObservationMarkdown(markdown) {
    const parsed = parseObservationMarkdown(markdown);
    if (parsed.length === 0) {
      return markdown.trim();
    }
    const grouped = /* @__PURE__ */ new Map();
    for (const record of parsed) {
      const bucket = grouped.get(record.date) ?? [];
      const normalized = normalizeObservationContent(record.content);
      const existingIndex = bucket.findIndex(
        (line) => normalizeObservationContent(line.content) === normalized
      );
      if (existingIndex === -1) {
        bucket.push({
          type: record.type,
          confidence: record.confidence,
          importance: record.importance,
          content: record.content
        });
      } else {
        const existing = bucket[existingIndex];
        bucket[existingIndex] = {
          type: record.importance >= existing.importance ? record.type : existing.type,
          confidence: Math.max(existing.confidence, record.confidence),
          importance: Math.max(existing.importance, record.importance),
          content: existing.content.length >= record.content.length ? existing.content : record.content
        };
      }
      grouped.set(record.date, bucket);
    }
    return renderObservationMarkdown(grouped);
  }
  persistRawMessages(messages, options) {
    const source = this.sanitizeSource(options.source ?? "openclaw");
    const messageTimestamp = options.timestamp ?? this.now();
    const rawPath = getRawTranscriptPath(this.vaultPath, source, messageTimestamp);
    ensureParentDir(rawPath);
    const records = messages.map((message) => JSON.stringify({
      recordedAt: this.now().toISOString(),
      timestamp: messageTimestamp.toISOString(),
      source,
      sessionKey: options.sessionKey ?? null,
      transcriptId: options.transcriptId ?? null,
      message
    }));
    fs2.appendFileSync(rawPath, `${records.join("\n")}
`, "utf-8");
  }
  sanitizeSource(source) {
    const normalized = source.trim().toLowerCase();
    if (/^[a-z0-9_-]{1,64}$/.test(normalized)) {
      return normalized;
    }
    return "openclaw";
  }
  mergeRouteContext(existing, incoming) {
    const merged = { ...existing };
    if (incoming.source) merged.source = incoming.source;
    if (incoming.sessionKey) merged.sessionKey = incoming.sessionKey;
    if (incoming.transcriptId) merged.transcriptId = incoming.transcriptId;
    if (incoming.timestamp) merged.timestamp = incoming.timestamp;
    return merged;
  }
};

export {
  Compressor,
  Reflector,
  Observer
};

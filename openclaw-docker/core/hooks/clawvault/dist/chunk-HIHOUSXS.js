// src/lib/llm-provider.ts
var DEFAULT_MODELS = {
  anthropic: "claude-3-5-haiku-latest",
  openai: "gpt-4o-mini",
  gemini: "gemini-2.0-flash"
};
function resolveLlmProvider() {
  if (process.env.CLAWVAULT_NO_LLM) {
    return null;
  }
  if (process.env.ANTHROPIC_API_KEY) {
    return "anthropic";
  }
  if (process.env.OPENAI_API_KEY) {
    return "openai";
  }
  if (process.env.GEMINI_API_KEY) {
    return "gemini";
  }
  return null;
}
async function requestLlmCompletion(options) {
  const provider = options.provider ?? resolveLlmProvider();
  if (!provider) {
    return "";
  }
  if (provider === "anthropic") {
    return callAnthropic(options, provider);
  }
  if (provider === "gemini") {
    return callGemini(options, provider);
  }
  return callOpenAI(options, provider);
}
async function callAnthropic(options, provider) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return "";
  }
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01"
    },
    body: JSON.stringify({
      model: options.model ?? DEFAULT_MODELS[provider],
      temperature: options.temperature ?? 0.1,
      max_tokens: options.maxTokens ?? 1200,
      messages: [{ role: "user", content: options.prompt }]
    })
  });
  if (!response.ok) {
    throw new Error(`Anthropic request failed (${response.status})`);
  }
  const payload = await response.json();
  return payload.content?.filter((entry) => entry.type === "text" && entry.text).map((entry) => entry.text).join("\n").trim() ?? "";
}
async function callOpenAI(options, provider) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    return "";
  }
  const fetchImpl = options.fetchImpl ?? fetch;
  const messages = [];
  if (options.systemPrompt?.trim()) {
    messages.push({ role: "system", content: options.systemPrompt.trim() });
  }
  messages.push({ role: "user", content: options.prompt });
  const response = await fetchImpl("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: options.model ?? DEFAULT_MODELS[provider],
      temperature: options.temperature ?? 0.1,
      max_tokens: options.maxTokens ?? 1200,
      messages
    })
  });
  if (!response.ok) {
    throw new Error(`OpenAI request failed (${response.status})`);
  }
  const payload = await response.json();
  return payload.choices?.[0]?.message?.content?.trim() ?? "";
}
async function callGemini(options, provider) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return "";
  }
  const fetchImpl = options.fetchImpl ?? fetch;
  const model = options.model ?? DEFAULT_MODELS[provider];
  const response = await fetchImpl(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
    {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify({
        contents: [{ parts: [{ text: options.prompt }] }],
        generationConfig: {
          temperature: options.temperature ?? 0.1,
          maxOutputTokens: options.maxTokens ?? 1200
        }
      })
    }
  );
  if (!response.ok) {
    throw new Error(`Gemini request failed (${response.status})`);
  }
  const payload = await response.json();
  return payload.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";
}

export {
  resolveLlmProvider,
  requestLlmCompletion
};

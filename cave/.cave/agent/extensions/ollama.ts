import type { ExtensionAPI } from "@juliusbrussee/caveman-code";

export default function (pi: ExtensionAPI) {
  pi.registerProvider("ollama", {
    baseUrl: "http://localhost:11434/v1",
    apiKey: "ollama",
    api: "openai-completions",
    models: [
      {
        id: "qwen3-14b",
        name: "Qwen3 14B (local)",
        reasoning: true,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 32768,
        maxTokens: 8192,
        compat: {
          supportsDeveloperRole: false,
          maxTokensField: "max_tokens",
          requiresToolResultName: true,
          requiresAssistantAfterToolResult: true,
          thinkingFormat: "qwen-chat-template",
        },
      },
    ],
  });
}

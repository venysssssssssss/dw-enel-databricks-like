import { fetchEventSource } from "@microsoft/fetch-event-source";

export type RagEventHandlers = {
  onToken: (token: string) => void;
  onDone: (payload: RagDonePayload) => void;
  onError: (message: string) => void;
};

export type RagDonePayload = {
  ok?: boolean;
  question_hash?: string;
  cache_hit?: boolean;
  cache_seed_id?: string | null;
  latency_ms?: number;
  intent?: string;
  tokens?: number;
  sources?: Array<{
    doc_id?: string;
    path?: string;
    score?: number;
    section?: string;
  }>;
};

export type RagHistoryTurn = {
  role: "user" | "assistant";
  content: string;
};

export async function streamRagAnswer(
  question: string,
  datasetHash: string,
  handlers: RagEventHandlers,
  signal?: AbortSignal,
  history: RagHistoryTurn[] = [],
  contextHint?: string
): Promise<void> {
  const body: Record<string, unknown> = { question, history };
  if (contextHint) body.context_hint = contextHint;
  await fetchEventSource("/v1/rag/stream", {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      "X-Dataset-Version": datasetHash
    },
    body: JSON.stringify(body),
    onmessage(event) {
      const payload = JSON.parse(event.data || "{}") as RagDonePayload & {
        text?: string;
        message?: string;
      };
      if (event.event === "token" && payload.text) {
        handlers.onToken(payload.text);
      }
      if (event.event === "done") {
        handlers.onDone(payload);
      }
      if (event.event === "error") {
        handlers.onError(payload.message ?? "Falha no stream RAG.");
      }
    },
    onerror(error) {
      handlers.onError(error instanceof Error ? error.message : "Falha no stream RAG.");
      throw error;
    }
  });
}

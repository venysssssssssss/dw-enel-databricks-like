import { fetchEventSource } from "@microsoft/fetch-event-source";

export type RagEventHandlers = {
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
};

export async function streamRagAnswer(
  question: string,
  datasetHash: string,
  handlers: RagEventHandlers,
  signal?: AbortSignal
): Promise<void> {
  await fetchEventSource("/v1/rag/stream", {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      "X-Dataset-Version": datasetHash
    },
    body: JSON.stringify({ question }),
    onmessage(event) {
      const payload = JSON.parse(event.data || "{}") as { text?: string; message?: string };
      if (event.event === "token" && payload.text) {
        handlers.onToken(payload.text);
      }
      if (event.event === "done") {
        handlers.onDone();
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

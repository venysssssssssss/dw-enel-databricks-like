import { useCallback, useEffect, useRef, useState } from "react";
import { streamRagAnswer } from "../lib/sse";

export type RagStage = {
  key: string;
  label: string;
  status: "pending" | "active" | "done" | "error";
};

export type RagSource = {
  doc_id?: string;
  path?: string;
  score?: number;
  section?: string;
  anchor?: string;
};

export type RagMeta = {
  intent?: string;
  tokens?: number;
  latency_ms?: number;
  first_token_ms?: number;
  sources_count?: number;
};

export type RagMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  questionHash?: string;
  cacheHit?: boolean;
  feedbackSent?: boolean;
  sources?: RagSource[];
  stages?: RagStage[];
  meta?: RagMeta;
  firstTokenAt?: number;
};

export function useRagStream(datasetHash: string, contextHint?: string) {
  const [messages, setMessages] = useState<RagMessage[]>([]);
  const [status, setStatus] = useState<"idle" | "streaming" | "done" | "error">("idle");
  const abortRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<RagMessage[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const ask = useCallback(
    async (question: string) => {
      if (!question.trim() || !datasetHash || datasetHash === "pending") {
        return;
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setStatus("streaming");
      const userId = makeMessageId("user");
      const assistantId = makeMessageId("assistant");
      const startedAt = Date.now();
      const history = messagesRef.current.slice(-8).map((turn) => ({
        role: turn.role,
        content: turn.content
      }));
      setMessages((current) => [
        ...current,
        { id: userId, role: "user", content: question, createdAt: startedAt },
        {
          id: assistantId,
          role: "assistant",
          content: "",
          createdAt: startedAt,
          stages: initialStages()
        }
      ]);
      await streamRagAnswer(
        question,
        datasetHash,
        {
          onToken(token) {
            setMessages((current) => {
              const copy = [...current];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = {
                ...last,
                content: `${last.content}${token}`,
                firstTokenAt: last.firstTokenAt ?? Date.now()
              };
              return copy;
            });
          },
          onStage(payload) {
            if (!payload.key) return;
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      stages: mergeStage(message.stages, {
                        key: payload.key ?? "stage",
                        label: payload.label ?? defaultStageLabel(payload.key ?? "stage"),
                        status: payload.status ?? "active"
                      })
                    }
                  : message
              )
            );
          },
          onDone(payload) {
            setStatus("done");
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      stages: (message.stages ?? initialStages()).map((stage) => ({
                        ...stage,
                        status: "done"
                      })),
                      questionHash: payload.question_hash,
                      cacheHit: Boolean(payload.cache_hit),
                      sources: payload.sources ?? [],
                      meta: {
                        intent: payload.intent,
                        tokens: payload.tokens,
                        latency_ms: payload.latency_ms,
                        first_token_ms: message.firstTokenAt
                          ? message.firstTokenAt - startedAt
                          : undefined,
                        sources_count: payload.sources?.length
                      }
                    }
                  : message
              )
            );
          },
          onError(message) {
            setStatus("error");
            setMessages((current) => {
              const copy = [...current];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = { ...last, content: last.content || message };
              return copy;
            });
          }
        },
        controller.signal,
        history,
        contextHint
      );
    },
    [datasetHash, contextHint]
  );

  const markFeedbackSent = useCallback((messageId: string) => {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? { ...message, feedbackSent: true } : message
      )
    );
  }, []);

  return { messages, status, ask, markFeedbackSent };
}

function makeMessageId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function initialStages(): RagStage[] {
  return [
    { key: "validate", label: "Validar pergunta", status: "active" },
    { key: "route", label: "Roteamento CE/SP", status: "pending" },
    { key: "retrieve", label: "Consultar silver e fontes", status: "pending" },
    { key: "generate", label: "Gerar resposta", status: "pending" }
  ];
}

function mergeStage(current: RagStage[] | undefined, next: RagStage): RagStage[] {
  const stages = current && current.length > 0 ? current : initialStages();
  let seen = false;
  const merged = stages.map((stage) => {
    if (stage.key !== next.key) return stage;
    seen = true;
    return { ...stage, ...next };
  });
  return seen ? merged : [...merged, next];
}

function defaultStageLabel(key: string): string {
  const stage = initialStages().find((item) => item.key === key);
  return stage?.label ?? key;
}

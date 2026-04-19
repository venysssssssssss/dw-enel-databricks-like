import { useCallback, useEffect, useRef, useState } from "react";
import { streamRagAnswer } from "../lib/sse";

export type RagMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  questionHash?: string;
  cacheHit?: boolean;
  feedbackSent?: boolean;
};

export function useRagStream(datasetHash: string) {
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
      const history = messagesRef.current.slice(-8).map((turn) => ({
        role: turn.role,
        content: turn.content
      }));
      setMessages((current) => [
        ...current,
        { id: userId, role: "user", content: question },
        { id: assistantId, role: "assistant", content: "" }
      ]);
      await streamRagAnswer(
        question,
        datasetHash,
        {
          onToken(token) {
            setMessages((current) => {
              const copy = [...current];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = { ...last, content: `${last.content}${token}` };
              return copy;
            });
          },
          onDone(payload) {
            setStatus("done");
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      questionHash: payload.question_hash,
                      cacheHit: Boolean(payload.cache_hit)
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
        history
      );
    },
    [datasetHash]
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

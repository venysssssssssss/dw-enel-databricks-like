import { useCallback, useEffect, useRef, useState } from "react";
import { streamRagAnswer } from "../lib/sse";

export type RagMessage = {
  role: "user" | "assistant";
  content: string;
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
      const history = messagesRef.current.slice(-8).map((turn) => ({
        role: turn.role,
        content: turn.content
      }));
      setMessages((current) => [
        ...current,
        { role: "user", content: question },
        { role: "assistant", content: "" }
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
          onDone() {
            setStatus("done");
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

  return { messages, status, ask };
}

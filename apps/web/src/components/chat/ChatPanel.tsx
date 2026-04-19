import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useRagStream } from "../../hooks/useRagStream";
import { sendRagFeedback } from "../../lib/api";

export function ChatPanel({ datasetHash }: { datasetHash: string }) {
  const [question, setQuestion] = useState("");
  const { messages, status, ask, markFeedbackSent } = useRagStream(datasetHash);

  async function handleFeedback(messageId: string, questionHash: string, rating: "up" | "down") {
    await sendRagFeedback(questionHash, rating);
    markFeedbackSent(messageId);
  }

  return (
    <section className="chat-panel" aria-label="Assistente ENEL">
      <div className="chat-log">
        {messages.length === 0 ? (
          <p className="empty-copy">Pergunte sobre KPIs, causas, regiões, sprint ou regras ACF/ASF.</p>
        ) : null}
        {messages.map((message) => (
          <article className={`message message--${message.role}`} key={message.id}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || "..."}</ReactMarkdown>
            {message.role === "assistant" && message.questionHash ? (
              <div className="feedback-row" aria-label="Avaliação da resposta">
                <button
                  type="button"
                  className="feedback-button feedback-button--up"
                  disabled={message.feedbackSent}
                  onClick={() => void handleFeedback(message.id, message.questionHash!, "up")}
                >
                  Útil
                </button>
                <button
                  type="button"
                  className="feedback-button feedback-button--down"
                  disabled={message.feedbackSent}
                  onClick={() => void handleFeedback(message.id, message.questionHash!, "down")}
                >
                  Não útil
                </button>
                {message.cacheHit ? <span className="cache-pill">cache</span> : null}
              </div>
            ) : null}
          </article>
        ))}
      </div>
      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          const value = question.trim();
          setQuestion("");
          void ask(value);
        }}
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ex.: qual região concentra mais ordens?"
          aria-label="Pergunta para o assistente"
        />
        <button type="submit" disabled={status === "streaming"}>
          {status === "streaming" ? "Gerando" : "Enviar"}
        </button>
      </form>
    </section>
  );
}

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useRagStream } from "../../hooks/useRagStream";

export function ChatPanel({ datasetHash }: { datasetHash: string }) {
  const [question, setQuestion] = useState("");
  const { messages, status, ask } = useRagStream(datasetHash);

  return (
    <section className="chat-panel" aria-label="Assistente ENEL">
      <div className="chat-log">
        {messages.length === 0 ? (
          <p className="empty-copy">Pergunte sobre KPIs, causas, regiões, sprint ou regras ACF/ASF.</p>
        ) : null}
        {messages.map((message, index) => (
          <article className={`message message--${message.role}`} key={`${message.role}-${index}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || "..."}</ReactMarkdown>
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

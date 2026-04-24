import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useRagStream, type RagMessage } from "../../hooks/useRagStream";
import { sendRagFeedback } from "../../lib/api";

const SUGGESTIONS: Array<{ cat: string; q: string }> = [
  { cat: "Dados · CE+SP", q: "Quantas reclamações temos no total?" },
  { cat: "Dados · top-N", q: "Quais os top 5 assuntos de reclamação?" },
  { cat: "Regras", q: "Como é calculado o flag ACF/ASF?" },
  { cat: "Modelos", q: "Qual a precisão do modelo de erro_leitura?" },
  { cat: "Arquitetura", q: "Como o silver é materializado no dbt?" },
  { cat: "Sprints", q: "O que entrou na Sprint 17?" }
];

type Props = {
  datasetHash: string;
  contextHint?: string;
};

export function ChatPanel({ datasetHash, contextHint }: Props) {
  const [draft, setDraft] = useState("");
  const { messages, status, ask, markFeedbackSent } = useRagStream(datasetHash, contextHint);
  const logRef = useRef<HTMLDivElement | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const node = logRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages]);

  function handleSubmit(value: string) {
    const v = value.trim();
    if (!v || status === "streaming") return;
    setDraft("");
    if (taRef.current) taRef.current.style.height = "auto";
    void ask(v);
  }

  async function handleFeedback(msg: RagMessage, rating: "up" | "down") {
    if (!msg.questionHash || msg.feedbackSent) return;
    await sendRagFeedback(msg.questionHash, rating);
    markFeedbackSent(msg.id);
  }

  return (
    <section className="chat-panel" aria-label="Assistente ENEL">
      <div className="chat-log" ref={logRef}>
        {messages.length === 0 ? (
          <>
            <div className="chat-intro">
              <h4>Como funciona</h4>
              <p>
                <b>Pergunta</b> livre ou clique em um card abaixo. O pipeline recupera trechos
                relevantes de <code>docs/</code> + data cards CE/SP e gera a resposta com
                citações.
                {contextHint ? (
                  <>
                    {" "}
                    <b>Contexto ativo:</b> <code>{contextHint}</code>.
                  </>
                ) : null}
              </p>
            </div>
            <div className="suggest">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.q}
                  type="button"
                  className="sug-card"
                  onClick={() => handleSubmit(s.q)}
                >
                  <span className="cat">{s.cat}</span>
                  <span className="q">{s.q}</span>
                </button>
              ))}
            </div>
          </>
        ) : null}

        <div className="messages">
          {messages.map((m) => (
            <MessageView
              key={m.id}
              message={m}
              streaming={status === "streaming" && m === messages[messages.length - 1]}
              onFeedback={(rating) => void handleFeedback(m, rating)}
            />
          ))}
        </div>
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            ref={taRef}
            rows={1}
            value={draft}
            placeholder="Pergunte sobre regras, modelos, dashboards ou arquitetura…"
            aria-label="Pergunta para o assistente"
            onChange={(e) => {
              setDraft(e.target.value);
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(draft);
              }
            }}
          />
          <div className="composer-foot">
            <div className="composer-hints">
              <span>
                <span className="kbd">⏎</span> enviar
              </span>
              <span>
                <span className="kbd">⇧⏎</span> nova linha
              </span>
            </div>
            <div className="composer-actions">
              <button
                type="button"
                className="composer-btn primary"
                disabled={status === "streaming" || !draft.trim()}
                onClick={() => handleSubmit(draft)}
              >
                <span>{status === "streaming" ? "Gerando…" : "Enviar"}</span>
                <span className="mono">⌘⏎</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

type MessageViewProps = {
  message: RagMessage;
  streaming: boolean;
  onFeedback: (rating: "up" | "down") => void;
};

function MessageView({ message, streaming, onFeedback }: MessageViewProps) {
  const isUser = message.role === "user";
  const time = new Date(message.createdAt).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit"
  });

  return (
    <div className={`msg ${isUser ? "user" : "assistant"}`}>
      <div className="msg-avatar">{isUser ? "VC" : "A"}</div>
      <div className="msg-body">
        <div className="msg-head">
          <span className="name">{isUser ? "Você" : "Assistente"}</span>
          {message.meta?.intent ? (
            <span className="badge">intent · {message.meta.intent}</span>
          ) : null}
          {message.cacheHit ? <span className="badge">cache</span> : null}
          <span className="time">{time}</span>
        </div>
        <div className="msg-text">
          {streaming && !message.content ? (
            <div className="typing" aria-live="polite">
              <div className="typing-label">
                <span className="pulse"></span>
                Recuperando passagens · gerando resposta
                <span className="caret"></span>
              </div>
              <div className="shimmer"></div>
              <div className="shimmer s2"></div>
              <div className="shimmer s3"></div>
            </div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || "…"}</ReactMarkdown>
          )}

          {!isUser && message.sources && message.sources.length > 0 ? (
            <div className="sources">
              <div className="sources-head">
                Fontes<span className="count">{message.sources.length}</span>
              </div>
              <div className="sources-list">
                {message.sources.map((src, i) => (
                  <button type="button" className="source" key={`${src.doc_id ?? src.path}-${i}`}>
                    <span className="n">{String(i + 1).padStart(2, "0")}</span>
                    <span className="path">
                      {src.path ?? src.doc_id ?? "…"}
                      {src.section ? (
                        <span style={{ color: "var(--text-faint)" }}> § {src.section}</span>
                      ) : null}
                    </span>
                    {typeof src.score === "number" ? (
                      <span className="score">{src.score.toFixed(2)}</span>
                    ) : null}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {!isUser && message.meta && !streaming ? (
            <div className="meta-row">
              {message.meta.tokens ? (
                <span className="pill ok">
                  <span className="k">tokens</span>
                  <span className="v">{message.meta.tokens.toLocaleString("pt-BR")}</span>
                </span>
              ) : null}
              {message.meta.latency_ms ? (
                <span className="pill">
                  <span className="k">⏱</span>
                  <span className="v">{(message.meta.latency_ms / 1000).toFixed(1)}s</span>
                </span>
              ) : null}
              {message.meta.first_token_ms ? (
                <span className="pill">
                  <span className="k">1º tok</span>
                  <span className="v">{message.meta.first_token_ms}ms</span>
                </span>
              ) : null}
              {message.meta.sources_count ? (
                <span className="pill">
                  <span className="k">fontes</span>
                  <span className="v">{message.meta.sources_count}</span>
                </span>
              ) : null}
            </div>
          ) : null}

          {!isUser && message.questionHash && !streaming ? (
            <div className="fb-row">
              <button
                type="button"
                className="fb-btn"
                aria-label="Útil"
                disabled={message.feedbackSent}
                onClick={() => onFeedback("up")}
              >
                ↑
              </button>
              <button
                type="button"
                className="fb-btn"
                aria-label="Não útil"
                disabled={message.feedbackSent}
                onClick={() => onFeedback("down")}
              >
                ↓
              </button>
              <button
                type="button"
                className="fb-btn"
                aria-label="Copiar"
                onClick={() => void navigator.clipboard?.writeText(message.content)}
              >
                ⧉
              </button>
              <span className="fb-txt" style={{ marginLeft: 6 }}>
                {message.feedbackSent ? "Obrigado pelo feedback" : "Feedback treina o retriever"}
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

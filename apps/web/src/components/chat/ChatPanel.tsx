import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useRagStream, type RagMessage, type RagStage } from "../../hooks/useRagStream";
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
          {message.meta?.model ? <span className="badge">modelo · {message.meta.model}</span> : null}
          {message.cacheHit ? <span className="badge">cache</span> : null}
          <span className="time">{time}</span>
        </div>
        <div className="msg-text">
          {!isUser && message.meta?.model ? (
            <RuntimePanel meta={message.meta} streaming={streaming} />
          ) : null}

          {streaming && !message.content ? (
            <div className="typing" aria-live="polite">
              <div className="typing-label">
                <span className="pulse"></span>
                Pipeline do agente em execução
                <span className="caret"></span>
              </div>
              <PipelineStages stages={message.stages} />
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
              {message.meta.provider ? (
                <span className="pill">
                  <span className="k">runtime</span>
                  <span className="v">{message.meta.provider}</span>
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

function RuntimePanel({
  meta,
  streaming
}: {
  meta: NonNullable<RagMessage["meta"]>;
  streaming: boolean;
}) {
  const items = [
    { key: "Provider", value: meta.provider ?? "local" },
    { key: "Modelo", value: meta.model ?? "desconhecido" },
    {
      key: "Threads",
      value: typeof meta.n_threads === "number" ? String(meta.n_threads) : "auto"
    },
    {
      key: "Retrieval",
      value:
        typeof meta.retrieval_k === "number" && typeof meta.rerank_top_n === "number"
          ? `k${meta.retrieval_k} / top${meta.rerank_top_n}`
          : "cards"
    },
    { key: "Escopo", value: meta.regional_scope ?? "CE+SP" }
  ];

  return (
    <div className={`runtime-panel ${streaming ? "is-live" : ""}`} aria-label="Runtime RAG">
      {items.map((item) => (
        <span className="runtime-item" key={item.key}>
          <span className="runtime-key">{item.key}</span>
          <span className="runtime-value">{item.value}</span>
        </span>
      ))}
    </div>
  );
}

const STAGE_HINT: Record<string, string> = {
  validate: "guardrails + classificação de intent",
  route: "decisão CE/SP + filtro de escopo",
  retrieve: "vetor + reranker + cards",
  generate: "geração com citações"
};

function PipelineStages({ stages }: { stages?: RagStage[] }) {
  const [now, setNow] = useState(() => Date.now());
  const startedRef = useRef<number>(Date.now());
  useEffect(() => {
    if (!stages || stages.length === 0) return;
    const id = window.setInterval(() => setNow(Date.now()), 120);
    return () => window.clearInterval(id);
  }, [stages]);

  if (!stages || stages.length === 0) return null;

  const total = stages.length;
  const doneCount = stages.filter((s) => s.status === "done").length;
  const activeCount = stages.filter((s) => s.status === "active").length;
  const progressed = Math.min(1, (doneCount + activeCount * 0.45) / total);
  const elapsed = ((now - startedRef.current) / 1000).toFixed(1);

  return (
    <section className="agent-pipeline" aria-label="Pipeline do agente">
      <header className="agent-pipeline-head">
        <span className="agent-pipeline-tag">PIPELINE</span>
        <span className="agent-pipeline-progress" aria-hidden>
          <span style={{ width: `${progressed * 100}%` }} />
        </span>
        <span className="agent-pipeline-stat" aria-live="polite">
          {String(doneCount).padStart(2, "0")}<span className="dim">/{String(total).padStart(2, "0")}</span>
          <span className="sep" aria-hidden>·</span>
          {elapsed}s
        </span>
      </header>
      <ol className="agent-pipeline-list" role="list">
        {stages.map((stage, idx) => {
          const hint = STAGE_HINT[stage.key];
          const glyph =
            stage.status === "done" ? "✓"
            : stage.status === "active" ? "●"
            : stage.status === "error" ? "×"
            : "○";
          return (
            <li className={`agent-step is-${stage.status}`} key={stage.key} role="listitem">
              <span className="agent-step-glyph" aria-hidden>{glyph}</span>
              <span className="agent-step-num" aria-hidden>{String(idx + 1).padStart(2, "0")}</span>
              <span className="agent-step-body">
                <span className="agent-label">{stage.label}</span>
                {hint ? <span className="agent-step-hint">{hint}</span> : null}
              </span>
              <span className="agent-step-state" aria-hidden />
            </li>
          );
        })}
      </ol>
    </section>
  );
}

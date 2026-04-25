import { useMemo, useState } from "react";
import { fmtMoney, fmtN } from "./SeverityCharts";

export type DescricaoRow = {
  id: string;
  cat: string;
  categoria_id: string;
  causa: string;
  data: string;
  proc: boolean;
  valor: number;
  resumo: string;
  sugestao: string;
  area: string;
  top_instalacoes: { inst: string; cidade: string; reinc: number; valor: number }[];
};

type Filter = "todas" | "procedentes" | "improcedentes";

export function DescricoesTable({
  rows,
  loading,
  activeCat,
  activeCausa
}: {
  rows: DescricaoRow[];
  loading?: boolean;
  activeCat?: string | null;
  activeCausa?: string | null;
}) {
  const [filter, setFilter] = useState<Filter>("todas");
  const [openId, setOpenId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let out = rows;
    if (activeCat) out = out.filter((r) => r.categoria_id === activeCat);
    if (activeCausa) out = out.filter((r) => r.causa === activeCausa);
    if (filter === "procedentes") out = out.filter((r) => r.proc);
    else if (filter === "improcedentes") out = out.filter((r) => !r.proc);
    return out;
  }, [rows, activeCat, activeCausa, filter]);

  if (loading) return <div className="sev-skeleton" style={{ height: 320 }} />;
  if (!rows.length) return <p className="sev-c-sub">Sem descrições disponíveis para esta severidade.</p>;

  return (
    <div className="desc-table-wrap">
      <div className="desc-toolbar">
        <div className="desc-filter">
          {(["todas", "procedentes", "improcedentes"] as Filter[]).map((f) => (
            <button
              key={f}
              type="button"
              className={"desc-chip" + (filter === f ? " is-on" : "")}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="desc-meta">
          {activeCat || activeCausa ? <span className="desc-filterhint">filtros cruzados ativos</span> : null}
          <span className="desc-count">
            {fmtN(filtered.length)} <span className="dim">de {fmtN(rows.length)}</span>
          </span>
        </div>
      </div>

      <div className="desc-scroll">
        <table className="desc-table">
          <thead>
            <tr>
              <th style={{ width: 132 }}>ID</th>
              <th>Categoria · causa canônica</th>
              <th style={{ width: 92 }}>Data</th>
              <th style={{ width: 110 }}>Status</th>
              <th style={{ width: 130 }} className="num">
                Valor fatura
              </th>
              <th style={{ width: 30 }} aria-hidden />
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const isOpen = openId === r.id;
              return (
                <DescriptionRow
                  key={r.id}
                  row={r}
                  open={isOpen}
                  onToggle={() => setOpenId(isOpen ? null : r.id)}
                />
              );
            })}
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="desc-empty">
                  Nenhuma descrição corresponde aos filtros atuais.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DescriptionRow({
  row,
  open,
  onToggle
}: {
  row: DescricaoRow;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={"desc-row" + (open ? " is-open" : "")}
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
      >
        <td>
          <span className="desc-id">{row.id}</span>
        </td>
        <td>
          <div className="desc-cat">{row.cat}</div>
          <div className="desc-causa">{row.causa}</div>
        </td>
        <td className="desc-date">{row.data || "—"}</td>
        <td>
          <span className={"desc-tag " + (row.proc ? "proc" : "improc")}>
            {row.proc ? "procedente" : "improcedente"}
          </span>
        </td>
        <td className="num desc-valor">{fmtMoney(row.valor)}</td>
        <td className="desc-chev" aria-hidden>
          ▶
        </td>
      </tr>
      {open ? (
        <tr className="desc-detail">
          <td colSpan={6}>
            <div className="desc-detail-body">
              <div className="desc-quote">{row.resumo || "—"}</div>
              <div className="desc-grid">
                <div className="desc-block">
                  <div className="desc-label">Ação sugerida (IA)</div>
                  <div className="desc-value">{row.sugestao}</div>
                </div>
                <div className="desc-block">
                  <div className="desc-label">Área responsável</div>
                  <div className="desc-value">{row.area}</div>
                </div>
                <div className="desc-block">
                  <div className="desc-label">Causa · categoria</div>
                  <div className="desc-value">
                    <code>{row.causa}</code> · <span className="dim">{row.cat}</span>
                  </div>
                </div>
              </div>
              <TopInstalacoes rows={row.top_instalacoes} />
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function TopInstalacoes({ rows }: { rows: DescricaoRow["top_instalacoes"] }) {
  if (!rows?.length) {
    return (
      <p className="desc-empty-sub">
        Sem reincidência suficiente nesta causa para compor top-10 instalações.
      </p>
    );
  }
  const max = Math.max(...rows.map((r) => r.reinc), 1);
  return (
    <div className="desc-instal">
      <div className="desc-instal-head">
        <span className="desc-instal-title">Top {rows.length} instalações reincidentes na mesma causa</span>
        <span className="desc-instal-sub">SP · ordenado por reincidência</span>
      </div>
      <table className="desc-instal-table">
        <thead>
          <tr>
            <th style={{ width: 28 }}>#</th>
            <th>Instalação</th>
            <th style={{ width: 120 }}>Cidade</th>
            <th style={{ width: 140 }}>Reincidência</th>
            <th style={{ width: 130 }} className="num">
              Valor fatura
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.inst + i}>
              <td>
                <span className="desc-pos">{i + 1}</span>
              </td>
              <td>
                <span className="desc-inst-id">{r.inst}</span>
              </td>
              <td className="dim">{r.cidade}</td>
              <td>
                <div className="desc-reinc">
                  <div className="desc-reinc-bar">
                    <span style={{ width: `${(r.reinc / max) * 100}%` }} />
                  </div>
                  <span className="desc-reinc-num">{r.reinc}×</span>
                </div>
              </td>
              <td className="num desc-valor">{fmtMoney(r.valor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

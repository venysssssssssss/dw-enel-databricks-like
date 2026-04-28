import { useMemo, useState } from "react";
import {
  formatCategoria,
  formatCausa,
  formatMoney,
  formatNumber,
  formatPercent,
  groupCategoriaSubcausaTree,
  type CategoriaSubcausaTreeRow,
  type CategoriaTreeNode
} from "../../lib/analytics";

export function ExpandableCategoryTree({
  rows,
  loading,
  emptyHint = "Sem categorias rotuladas para o recorte atual."
}: {
  rows: CategoriaSubcausaTreeRow[];
  loading?: boolean;
  emptyHint?: string;
}) {
  const tree = useMemo(() => groupCategoriaSubcausaTree(rows), [rows]);
  const [openCat, setOpenCat] = useState<string | null>(tree[0]?.categoria_id ?? null);
  const [drawerKey, setDrawerKey] = useState<string | null>(null);

  if (loading) {
    return <div className="sev-skeleton" style={{ height: 320 }} />;
  }
  if (!tree.length) {
    return <div className="cat-tree cat-tree--empty">{emptyHint}</div>;
  }

  const drawerRow = drawerKey ? rows.find((r) => `${r.categoria_id}::${r.subcausa_id}` === drawerKey) ?? null : null;

  return (
    <div className="cat-tree" role="tree">
      {tree.map((node) => (
        <CategoryNode
          key={node.categoria_id}
          node={node}
          open={openCat === node.categoria_id}
          onToggle={() =>
            setOpenCat((cur) => (cur === node.categoria_id ? null : node.categoria_id))
          }
          onOpenSub={(row) =>
            setDrawerKey(`${row.categoria_id}::${row.subcausa_id}`)
          }
          activeKey={drawerKey}
        />
      ))}
      {drawerRow ? (
        <RealExampleDrawer row={drawerRow} onClose={() => setDrawerKey(null)} />
      ) : null}
    </div>
  );
}

function CategoryNode({
  node,
  open,
  onToggle,
  onOpenSub,
  activeKey
}: {
  node: CategoriaTreeNode;
  open: boolean;
  onToggle: () => void;
  onOpenSub: (row: CategoriaSubcausaTreeRow) => void;
  activeKey: string | null;
}) {
  const total = node.procedentes + node.improcedentes;
  const pctProc = total > 0 ? (node.procedentes / total) * 100 : 0;
  const max = Math.max(1, ...node.subcausas.map((r) => r.qtd));
  return (
    <div className={"cat-tree-node" + (open ? " is-open" : "")} role="treeitem" aria-expanded={open}>
      <button type="button" className="cat-tree-cat" onClick={onToggle}>
        <span className="cat-tree-chev" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="cat-tree-cat-label">{formatCategoria(node.categoria_label)}</span>
        <span className="cat-tree-cat-vol">
          <b>{formatNumber(node.categoria_qtd)}</b>
        </span>
        <span className="cat-tree-cat-pct">{formatPercent(node.categoria_pct)}</span>
        <span className="cat-tree-cat-split" title="procedentes / improcedentes (contagem real)">
          <span className="proc">{formatNumber(node.procedentes)} proc</span>
          <span className="sep">·</span>
          <span className="improc">{formatNumber(node.improcedentes)} improc</span>
          <span className="pct">({formatPercent(pctProc)} proc)</span>
        </span>
      </button>
      {open ? (
        <ul className="cat-tree-subs" role="group">
          {node.subcausas.map((row) => {
            const w = (row.qtd / max) * 100;
            const key = `${row.categoria_id}::${row.subcausa_id}`;
            const isActive = activeKey === key;
            const totalSub = row.procedentes + row.improcedentes;
            const pctProcSub = totalSub > 0 ? (row.procedentes / totalSub) * 100 : 0;
            return (
              <li key={key} className={"cat-tree-sub" + (isActive ? " is-active" : "")}>
                <button type="button" className="cat-tree-sub-btn" onClick={() => onOpenSub(row)}>
                  <span className="cat-tree-sub-label">{formatCausa(row.subcausa_label)}</span>
                  <span className="cat-tree-sub-bar">
                    <span style={{ width: `${w}%` }} />
                  </span>
                  <span className="cat-tree-sub-vol">{formatNumber(row.qtd)}</span>
                  <span className="cat-tree-sub-pct">
                    {formatPercent(row.percentual_na_categoria)}
                  </span>
                  <span className="cat-tree-sub-split">
                    <span className="proc">{formatNumber(row.procedentes)}</span>
                    <span className="sep">/</span>
                    <span className="improc">{formatNumber(row.improcedentes)}</span>
                    <span className="pct"> · {formatPercent(pctProcSub)} proc</span>
                  </span>
                  <span className="cat-tree-sub-cta" aria-hidden>
                    ver exemplo →
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

function RealExampleDrawer({
  row,
  onClose
}: {
  row: CategoriaSubcausaTreeRow;
  onClose: () => void;
}) {
  const has = Boolean(row.exemplo_descricao && row.exemplo_descricao.trim().length > 0);
  return (
    <aside className="cat-drawer" role="dialog" aria-modal="false" aria-label="Exemplo real da subcausa">
      <header className="cat-drawer-head">
        <div>
          <div className="cat-drawer-eyebrow">
            {formatCategoria(row.categoria_label)} · {formatCausa(row.subcausa_label)}
          </div>
          <h3 className="cat-drawer-title">Exemplo real do dataset</h3>
        </div>
        <button type="button" className="cat-drawer-close" onClick={onClose} aria-label="Fechar">
          ✕
        </button>
      </header>
      <div className="cat-drawer-body">
        {has ? (
          <>
            <blockquote className="cat-drawer-quote">{row.exemplo_descricao}</blockquote>
            <dl className="cat-drawer-meta">
              <div>
                <dt>ID</dt>
                <dd><code>{row.exemplo_id || "—"}</code></dd>
              </div>
              <div>
                <dt>Data</dt>
                <dd>{row.exemplo_data || "—"}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <span className={"cat-drawer-tag " + (row.exemplo_status === "procedente" ? "proc" : "improc")}>
                    {row.exemplo_status || "—"}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Valor fatura</dt>
                <dd>{row.exemplo_valor_fatura > 0 ? formatMoney(row.exemplo_valor_fatura) : "—"}</dd>
              </div>
              <div>
                <dt>Causa canônica (ID)</dt>
                <dd><code className="dim">{row.subcausa_id}</code></dd>
              </div>
              <div>
                <dt>Categoria</dt>
                <dd>{formatCategoria(row.categoria_label)}</dd>
              </div>
            </dl>
            {row.recomendacao_operacional ? (
              <div className="cat-drawer-reco">
                <span className="lbl">Recomendação operacional</span>
                <p>{row.recomendacao_operacional}</p>
              </div>
            ) : null}
          </>
        ) : (
          <p className="cat-drawer-empty">
            Sem exemplo disponível no recorte atual. A view{" "}
            <code>sp_categoria_subcausa_tree</code> só retorna textos reais já presentes no
            silver — nada é inventado.
          </p>
        )}
      </div>
    </aside>
  );
}

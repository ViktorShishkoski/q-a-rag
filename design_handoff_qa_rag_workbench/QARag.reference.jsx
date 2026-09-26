import { useEffect, useRef, useState } from "react";

/**
 * Design reference — Tailwind translation of "Option A - Light workbench".
 * Assumes the theme tokens in tailwind.tokens.md. Split into your own
 * components and swap the mock data / timer for your real API.
 */

const DOCS = [
  { title: "Fundamentals of Data Engineering", kind: "pdf", chunks: 623 },
  { title: "Internal RAG eval notes", kind: "md", chunks: 41 },
];

const SUGGESTIONS = [
  "What are the stages of the data engineering lifecycle?",
  "How is ELT different from ETL?",
  "When should I choose a columnar store?",
];

const SOURCES = [
  { n: 1, loc: "p. 84 · c/311", score: 0.87, snippet: "The data engineering lifecycle comprises five stages: generation, storage, ingestion, transformation, and serving data." },
  { n: 2, loc: "p. 86 · c/318", score: 0.79, snippet: "Undercurrents cut across the lifecycle — security, data management, DataOps, architecture, orchestration, and software engineering." },
  { n: 3, loc: "p. 91 · c/340", score: 0.64, snippet: "Storage is not a discrete stage; it underpins ingestion, transformation, and serving throughout the lifecycle." },
];

const STAGES = (k) => ["searching index…", `reranking ${k * 4} candidates…`, "drafting answer…"];

const LABEL = "font-mono text-[10px] uppercase tracking-[0.09em] text-ink-7";
const CARD = "bg-surface border border-line rounded-xl shadow-card";
const PILL_BTN = "px-2.5 py-[5px] border border-line rounded-[7px] bg-surface text-[12px] text-ink-5 cursor-pointer hover:border-[#d3cec5]";

export default function QARag() {
  const [query, setQuery] = useState("What are the stages of the data engineering lifecycle?");
  const [topK, setTopK] = useState(5);
  const [rerank, setRerank] = useState(true);
  const [scopeAll, setScopeAll] = useState(true);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [answered, setAnswered] = useState(true);
  const [hovered, setHovered] = useState(null);
  const timer = useRef(null);

  useEffect(() => () => clearInterval(timer.current), []);

  function ask() {
    if (!query.trim()) return;
    clearInterval(timer.current);
    setBusy(true);
    setAnswered(false);
    setStage(0);
    timer.current = setInterval(() => {
      setStage((s) => {
        if (s >= 2) {
          clearInterval(timer.current);
          setBusy(false);
          setAnswered(true);
          return 0;
        }
        return s + 1;
      });
    }, 750);
  }

  const Cite = ({ n }) => (
    <sup
      onMouseEnter={() => setHovered(n)}
      onMouseLeave={() => setHovered(null)}
      className={`ml-0.5 inline-block min-w-[15px] rounded-[3px] px-[3px] py-px text-center align-super font-mono text-[9.5px] leading-[13px] cursor-pointer transition-colors duration-100 ${
        hovered === n ? "bg-accent text-white" : "bg-accent-tint text-accent"
      }`}
    >
      {n}
    </sup>
  );

  const chunkCount = DOCS.reduce((a, d) => a + d.chunks, 0);

  return (
    <div className="flex min-h-screen flex-col bg-page text-ink">
      <header className="sticky top-0 z-10 flex h-[60px] items-center justify-between gap-6 border-b border-line bg-brand-bar px-7">
        <div className="flex items-baseline gap-3 rounded-[5px] bg-[linear-gradient(180deg,#69D9CF,#F4EAE0)]">
          <span className="text-[16px] font-bold tracking-[-0.01em] text-brand-ink">Q&amp;A RAG</span>
          <span className="font-mono text-[11px] tracking-[0.04em] text-brand-ink-2">retrieval console</span>
        </div>
        <div className="flex items-center gap-[18px]">
          <div className="flex items-center gap-4 font-mono text-[11px] text-ink-6">
            <span>{DOCS.length} docs</span>
            <span>{chunkCount} chunks</span>
          </div>
          <div className="flex items-center gap-[7px] rounded-full border border-[#d7e5e3] bg-[#f0f7f6] py-[5px] pl-[9px] pr-[11px]">
            <span className="h-1.5 w-1.5 rounded-full bg-ok animate-pulse-dot" />
            <span className="font-mono text-[11px] tracking-[0.02em] text-ok-ink">healthy</span>
          </div>
        </div>
      </header>

      <div className="grid flex-1 items-start grid-cols-[300px_minmax(0,1fr)]">
        <aside className="sticky top-[60px] flex min-h-[calc(100vh-60px)] flex-col gap-[22px] border-r border-line bg-surface px-5 py-[22px]">
          <div>
            <div className={`${LABEL} mb-2.5`}>Corpus</div>
            <label
              htmlFor="fileInput"
              className="flex cursor-pointer flex-col items-center gap-2 rounded-[10px] border border-dashed border-line-dashed bg-surface-2 px-3.5 py-5 text-center transition-colors duration-150 hover:border-accent-hover hover:bg-[#f4f8f9]"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8c867d" strokeWidth="1.6" strokeLinecap="round">
                <path d="M12 16V4" />
                <path d="M7 9l5-5 5 5" />
                <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
              </svg>
              <div className="text-[12.5px] leading-[1.5] text-ink-5">
                Drop a <strong className="font-semibold text-[#3d3a35]">PDF</strong> or{" "}
                <strong className="font-semibold text-[#3d3a35]">Markdown</strong> file
                <br />
                or click to browse
              </div>
            </label>
            <input id="fileInput" type="file" className="hidden" />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className={LABEL}>Indexed</div>
              <div className="font-mono text-[10px] text-[#c2bcb2]">{DOCS.length}</div>
            </div>
            {DOCS.map((doc, i) => (
              <button
                key={doc.title}
                onClick={() => setSelected(i)}
                className={`rounded-[9px] border px-[11px] py-2.5 text-left transition-colors duration-150 ${
                  selected === i
                    ? "border-accent-border bg-[#f4f9fa]"
                    : "border-line-3 bg-surface-3 hover:border-[#d8d3ca] hover:bg-surface"
                }`}
              >
                <div className="flex items-start gap-[9px]">
                  <span className={`mt-[5px] h-1.5 w-1.5 shrink-0 rounded-[2px] ${selected === i ? "bg-accent-hover" : "bg-[#d3cec5]"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[12.5px] font-medium leading-[1.4] text-ink-3">{doc.title}</div>
                    <div className="mt-[5px] flex items-center gap-2 font-mono text-[10.5px] text-ink-7">
                      <span className="rounded-[3px] border border-line-2 px-[5px] py-px uppercase tracking-[0.04em]">{doc.kind}</span>
                      <span>{doc.chunks} chunks</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-auto border-t border-line-3 pt-4 font-mono text-[10.5px] leading-[1.7] text-ink-8">
            <div>embed · bge-small-en</div>
            <div>gen · gpt-4o-mini</div>
          </div>
        </aside>

        <main className="flex w-full max-w-[980px] flex-col gap-[22px] bg-white px-[34px] pb-[60px] pt-[30px]">
          <section className={CARD}>
            <textarea
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  ask();
                }
              }}
              placeholder="Ask a question about your documents…"
              className="w-full resize-none border-0 bg-transparent px-5 pb-1 pt-[18px] text-[16px] leading-[1.55] tracking-[-0.005em] text-ink outline-none"
            />
            <div className="flex items-center justify-between gap-5 border-t border-line-4 py-3 pl-5 pr-4">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] tracking-[0.03em] text-ink-6">top k</span>
                  <div className="flex items-center overflow-hidden rounded-[7px] border border-line-2 bg-surface-2">
                    <button onClick={() => setTopK((k) => Math.max(1, k - 1))} className="h-[26px] w-6 text-[14px] leading-none text-ink-5 hover:bg-line-3">−</button>
                    <span className="min-w-6 text-center font-mono text-[12px] text-ink-3">{topK}</span>
                    <button onClick={() => setTopK((k) => Math.min(20, k + 1))} className="h-[26px] w-6 text-[14px] leading-none text-ink-5 hover:bg-line-3">+</button>
                  </div>
                </div>

                <button
                  onClick={() => setRerank((r) => !r)}
                  className={`flex items-center gap-[7px] rounded-[7px] border px-[9px] py-[5px] ${
                    rerank ? "border-accent-border bg-accent-surface text-accent" : "border-line-2 bg-surface-2 text-ink-5"
                  }`}
                >
                  <span className={`h-[11px] w-[11px] rounded-[3px] border ${rerank ? "border-accent bg-accent shadow-[inset_0_0_0_2px_#f2f8f9]" : "border-line-dashed"}`} />
                  <span className="font-mono text-[11px] tracking-[0.03em]">rerank</span>
                </button>

                <button onClick={() => setScopeAll((s) => !s)} className="rounded-[7px] border border-line-2 bg-surface-2 px-[9px] py-[5px] font-mono text-[11px] tracking-[0.03em] text-ink-5 hover:border-[#d3cec5]">
                  {scopeAll ? "all documents" : `${DOCS[selected].kind} only`}
                </button>
              </div>

              <button
                onClick={ask}
                className={`flex items-center gap-2 rounded-lg px-4 py-[9px] text-[13.5px] font-semibold text-white shadow-btn ${busy ? "cursor-wait bg-accent-busy" : "bg-accent"}`}
              >
                {busy && <span className="h-1.5 w-1.5 rounded-full bg-current animate-[pulseDot_1s_ease-in-out_infinite]" />}
                <span>{busy ? "Asking" : "Ask"}</span>
                <span className="font-mono text-[10.5px] opacity-60">⏎</span>
              </button>
            </div>
          </section>

          {!busy && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="mr-1 font-mono text-[10.5px] uppercase tracking-[0.06em] text-ink-8">try</span>
              {SUGGESTIONS.map((text) => (
                <button
                  key={text}
                  onClick={() => setQuery(text)}
                  className="rounded-full border border-line bg-surface px-[11px] py-1.5 text-[12.5px] text-[#5c574f] transition-colors duration-150 hover:border-[oklch(0.7_0.06_205)] hover:text-accent-hover"
                >
                  {text}
                </button>
              ))}
            </div>
          )}

          {busy && (
            <section className={`${CARD} p-[22px]`}>
              <div className="mb-4 font-mono text-[11px] tracking-[0.04em] text-accent">{STAGES(topK)[stage]}</div>
              <div className="flex flex-col gap-2.5">
                {["92%", "78%", "55%"].map((w) => (
                  <div
                    key={w}
                    style={{ width: w }}
                    className="h-[11px] rounded-[3px] bg-[linear-gradient(90deg,#f1eee9_0%,#e6e2db_50%,#f1eee9_100%)] bg-[length:320px_100%] animate-shimmer"
                  />
                ))}
              </div>
            </section>
          )}

          {answered && (
            <section className="grid items-start gap-5 grid-cols-[minmax(0,1fr)_300px]">
              <article className={`${CARD} px-[26px] py-6`}>
                <div className="mb-3.5 flex items-center justify-between gap-4">
                  <div className={LABEL}>Answer</div>
                  <div className="flex items-center gap-3 font-mono text-[10.5px] text-ink-8">
                    <span>1.24s</span>
                    <span>412 tok</span>
                  </div>
                </div>
                <div className="text-[15.5px] leading-[1.68] text-ink-2 text-pretty">
                  The lifecycle runs in five stages — generation, storage, ingestion, transformation, and serving — each feeding the next rather than acting as an isolated step.
                  <Cite n={1} /> Storage sits slightly apart: it is treated as a stage but in practice underpins ingestion, transformation, and serving throughout.
                  <Cite n={3} /> Cutting across all of them are the undercurrents: security, data management, DataOps, architecture, orchestration, and software engineering.
                  <Cite n={2} />
                </div>
                <div className="mt-[22px] flex items-center gap-2 border-t border-line-4 pt-4">
                  <button className={PILL_BTN}>Copy</button>
                  <button className={PILL_BTN}>Regenerate</button>
                  <div className="ml-auto flex gap-1.5">
                    <button className="h-7 w-7 rounded-[7px] border border-line bg-surface text-[12px] text-ink-6 hover:border-[#d3cec5]">↑</button>
                    <button className="h-7 w-7 rounded-[7px] border border-line bg-surface text-[12px] text-ink-6 hover:border-[#d3cec5]">↓</button>
                  </div>
                </div>
              </article>

              <aside className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between">
                  <div className={LABEL}>Retrieved</div>
                  <div className="font-mono text-[10px] text-[#c2bcb2]">{SOURCES.length}</div>
                </div>
                {SOURCES.map((src) => {
                  const on = hovered === src.n;
                  return (
                    <div
                      key={src.n}
                      onMouseEnter={() => setHovered(src.n)}
                      onMouseLeave={() => setHovered(null)}
                      className={`rounded-[10px] border px-[13px] py-3 transition-colors duration-100 ${
                        on ? "border-accent-border-strong bg-[#f6fbfb] shadow-lift" : "border-line bg-surface"
                      }`}
                    >
                      <div className="mb-[7px] flex items-center justify-between gap-2.5">
                        <span className={`min-w-[18px] rounded-[4px] px-[5px] py-px text-center font-mono text-[10.5px] ${on ? "bg-accent text-white" : "bg-accent-tint text-accent"}`}>
                          {src.n}
                        </span>
                        <span className="font-mono text-[10.5px] text-ink-7">{src.loc}</span>
                      </div>
                      <div className="text-[12.5px] leading-[1.55] text-ink-4">{src.snippet}</div>
                      <div className="mt-[9px] flex items-center gap-2">
                        <div className="h-[3px] flex-1 overflow-hidden rounded-[2px] bg-line-3">
                          <div style={{ width: `${src.score * 100}%` }} className={`h-full ${on ? "bg-accent" : "bg-accent-muted"}`} />
                        </div>
                        <span className="font-mono text-[10.5px] text-ink-6">{src.score.toFixed(2)}</span>
                      </div>
                    </div>
                  );
                })}
              </aside>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

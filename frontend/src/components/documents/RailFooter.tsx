/** Rail footer — the model provenance line, pinned to the bottom of the corpus
 * rail. Values mirror the backend defaults (see CLAUDE.md / .env.example). */
export function RailFooter() {
  return (
    <div className="mt-auto border-t border-line-3 pt-4 font-mono text-[10.5px] leading-[1.7] text-ink-8">
      <div>embed · bge-small-en-v1.5</div>
      <div>gen · qwen3:1.7b</div>
    </div>
  );
}

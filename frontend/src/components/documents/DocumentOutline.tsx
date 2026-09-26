import { useOutline } from "@/api/queries";
import type { OutlineNode } from "@/api/types";
import { Skeleton } from "@/components/ui/skeleton";

interface DocumentOutlineProps {
  documentId: string;
  /** Only fetch when the row is expanded. */
  open: boolean;
}

function OutlineList({ nodes }: { nodes: OutlineNode[] }) {
  return (
    <ul className="flex flex-col gap-0.5">
      {nodes.map((node, i) => (
        <li key={`${node.section_path}-${i}`}>
          <div
            className="flex items-baseline justify-between gap-2 text-xs"
            style={{ paddingLeft: `${(node.level - 1) * 12}px` }}
          >
            <span className="truncate text-muted-foreground">{node.title}</span>
            {node.page !== null && (
              <span className="shrink-0 tabular-nums text-muted-foreground/70">p.{node.page}</span>
            )}
          </div>
          {node.children.length > 0 && <OutlineList nodes={node.children} />}
        </li>
      ))}
    </ul>
  );
}

export function DocumentOutline({ documentId, open }: DocumentOutlineProps) {
  const { data, isLoading, isError } = useOutline(documentId, open);

  if (!open) return null;
  if (isLoading) return <Skeleton className="ml-2 h-16 w-full" />;
  if (isError) return <p className="ml-2 text-xs text-destructive">Could not load outline.</p>;

  const outline = data?.outline ?? [];
  if (outline.length === 0) {
    return <p className="ml-2 text-xs text-muted-foreground">No headings detected.</p>;
  }

  return (
    <div className="ml-2 border-l pl-2">
      <OutlineList nodes={outline} />
    </div>
  );
}

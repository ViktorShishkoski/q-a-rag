import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useDocuments } from "@/api/queries";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { DocumentList } from "@/components/documents/DocumentList";
import { RailFooter } from "@/components/documents/RailFooter";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { AppShell } from "@/components/layout/AppShell";
import { SectionLabel } from "@/components/layout/SectionLabel";
import { Toaster } from "@/components/ui/sonner";

const queryClient = new QueryClient();

function Console() {
  const { data } = useDocuments();
  const documents = data?.documents ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedDoc = documents.find((d) => d.document_id === selectedId) ?? null;

  return (
    <AppShell
      rail={
        <>
          <div className="flex flex-col gap-2.5">
            <SectionLabel>Corpus</SectionLabel>
            <UploadDropzone />
          </div>
          <DocumentList selectedId={selectedId} onSelect={setSelectedId} />
          <RailFooter />
        </>
      }
    >
      <ChatPanel selectedDoc={selectedDoc} />
    </AppShell>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Console />
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;

import { useMemo, useState } from "react";
import CandidateDetail from "./components/CandidateDetail";
import CandidateTable from "./components/CandidateTable";
import Dashboard from "./components/Dashboard";
import Upload from "./components/Upload";

function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  const triggerRefresh = () => setRefreshKey((v) => v + 1);

  const heading = useMemo(
    () => "TALASH Milestone 1 Prototype: CV Ingestion, Extraction, and Candidate Dashboard",
    []
  );

  return (
    <main className="min-h-screen px-4 py-8 md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-xl border border-sky-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-talashBlue md:text-3xl">{heading}</h1>
          <p className="mt-2 text-sm text-slate-600">
            Upload CV PDFs, process candidates, and review extracted structured information.
          </p>
        </header>

        <Upload onProcessed={triggerRefresh} />

        <Dashboard refreshKey={refreshKey} />

        <CandidateTable
          refreshKey={refreshKey}
          onSelectCandidate={(candidate) => setSelectedCandidate(candidate)}
        />

        <CandidateDetail candidate={selectedCandidate} />
      </div>
    </main>
  );
}

export default App;

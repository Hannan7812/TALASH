import { useEffect, useState } from "react";
import { fetchCandidates } from "../services/api";

function CandidateTable({ refreshKey, onSelectCandidate }) {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchCandidates()
      .then((rows) => {
        if (mounted) setCandidates(rows);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [refreshKey]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-talashTeal">Candidate List</h2>
      {loading ? <p className="mt-3 text-sm">Loading candidates...</p> : null}
      {!loading && candidates.length === 0 ? <p className="mt-3 text-sm">No candidates found yet.</p> : null}
      {!loading && candidates.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-left text-slate-700">
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Email</th>
                <th className="px-2 py-2">Skills</th>
                <th className="px-2 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((row) => (
                <tr key={row.id} className="border-b border-slate-200">
                  <td className="px-2 py-2">{row.id}</td>
                  <td className="px-2 py-2">{row.full_name || "-"}</td>
                  <td className="px-2 py-2">{row.email || "-"}</td>
                  <td className="px-2 py-2">{row.skills_csv || "-"}</td>
                  <td className="px-2 py-2">
                    <button
                      onClick={() => onSelectCandidate(row)}
                      className="rounded bg-talashTeal px-3 py-1 text-white"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default CandidateTable;

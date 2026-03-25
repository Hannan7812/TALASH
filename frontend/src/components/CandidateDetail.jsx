import { useEffect, useState } from "react";
import { fetchCandidateDetail, fetchEmailDraft } from "../services/api";

function CandidateDetail({ candidate }) {
  const [detail, setDetail] = useState(null);
  const [emailDraft, setEmailDraft] = useState("");

  useEffect(() => {
    if (!candidate?.id) {
      setDetail(null);
      setEmailDraft("");
      return;
    }

    fetchCandidateDetail(candidate.id)
      .then(setDetail)
      .catch(() => setDetail(null));

    fetchEmailDraft(candidate.id)
      .then((res) => setEmailDraft(res.draft || ""))
      .catch(() => setEmailDraft(""));
  }, [candidate]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-talashTeal">Candidate Analysis + Email Draft View</h2>
      {!candidate ? <p className="mt-3 text-sm">Select a candidate to view detail.</p> : null}
      {detail ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-md bg-slate-50 p-3">
            <h3 className="font-semibold">Extracted JSON</h3>
            <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap text-xs">{detail.parsed_json}</pre>
          </div>
          <div className="rounded-md bg-slate-50 p-3">
            <h3 className="font-semibold">Missing Information Email Draft</h3>
            <pre className="mt-2 whitespace-pre-wrap text-xs">{emailDraft || "No draft available."}</pre>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default CandidateDetail;

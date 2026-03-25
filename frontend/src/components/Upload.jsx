import { useState } from "react";
import { processFolder } from "../services/api";

function Upload({ onProcessed }) {
  const [folderPath, setFolderPath] = useState("backend/data/raw_cvs");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await processFolder(folderPath, true);
      setResult(data);
      onProcessed();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-talashTeal">CV Folder Processing</h2>
      <form onSubmit={handleSubmit} className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
        <input
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          placeholder="Absolute or relative folder path containing PDFs"
          className="rounded-md border border-slate-300 px-3 py-2"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-talashBlue px-4 py-2 font-medium text-white disabled:opacity-60"
        >
          {loading ? "Processing..." : "Process Folder"}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {result ? (
        <div className="mt-4 rounded-md bg-talashSand p-3 text-sm">
          <p>Processed: {result.processed_count}</p>
          <p>Skipped: {result.skipped_count}</p>
          <p>Failed: {result.failed_count}</p>
        </div>
      ) : null}
    </section>
  );
}

export default Upload;

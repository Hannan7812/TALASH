import { useMemo, useState } from 'react';
import {
  detectMissingInformation,
  draftMissingInfoEmail,
  extractEducationSignals,
  extractExperienceSignals,
  extractResearchSignals,
} from '../lib/profileParsers';

function pct(value, total) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function scoreBand(score) {
  if (score == null || Number.isNaN(Number(score))) return 'unknown';
  const numeric = Number(score);
  if (numeric >= 75) return 'high';
  if (numeric >= 50) return 'medium';
  return 'low';
}

export default function AnalyticsReportsPage({
  candidates,
  loading,
  selectedCandidate,
  selectedCandidateId,
  selectCandidate,
}) {
  const [copied, setCopied] = useState(false);

  const reportRows = useMemo(
    () =>
      (candidates || []).map((candidate) => {
        const missing = detectMissingInformation(candidate);
        return {
          id: candidate.id,
          name: candidate.full_name || candidate.filename || `candidate_${candidate.id}`,
          email: candidate.email || '—',
          status: candidate.status || 'pending',
          score: candidate.overall_score,
          missingCount: missing.length,
          missing,
          uploadedAt: candidate.uploaded_at,
        };
      }),
    [candidates],
  );

  const chartStats = useMemo(() => {
    const total = reportRows.length;
    const completed = reportRows.filter((row) => row.status === 'completed').length;
    const processing = reportRows.filter((row) => row.status === 'processing').length;
    const pending = reportRows.filter((row) => row.status === 'pending').length;
    const failed = reportRows.filter((row) => row.status === 'failed').length;

    const withMissing = reportRows.filter((row) => row.missingCount > 0).length;

    const scoreHigh = reportRows.filter((row) => scoreBand(row.score) === 'high').length;
    const scoreMedium = reportRows.filter((row) => scoreBand(row.score) === 'medium').length;
    const scoreLow = reportRows.filter((row) => scoreBand(row.score) === 'low').length;

    return {
      total,
      completed,
      processing,
      pending,
      failed,
      withMissing,
      scoreHigh,
      scoreMedium,
      scoreLow,
    };
  }, [reportRows]);

  const details = useMemo(() => {
    if (!selectedCandidate) return null;

    const missingFields = detectMissingInformation(selectedCandidate);
    const emailDraft = draftMissingInfoEmail(selectedCandidate, missingFields);

    return {
      missingFields,
      emailDraft,
      education: extractEducationSignals(selectedCandidate.raw_text),
      research: extractResearchSignals(selectedCandidate.raw_text),
      experience: extractExperienceSignals(selectedCandidate.raw_text),
    };
  }, [selectedCandidate]);

  async function copyDraftEmail() {
    if (!details?.emailDraft) return;
    try {
      await navigator.clipboard.writeText(details.emailDraft);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="page-grid">
      <section className="summary-strip reveal">
        <article className="summary-tile">
          <p>Total Candidates</p>
          <strong>{chartStats.total}</strong>
        </article>
        <article className="summary-tile">
          <p>Completed Analyses</p>
          <strong>{chartStats.completed}</strong>
        </article>
        <article className="summary-tile">
          <p>Profiles Missing Data</p>
          <strong>{chartStats.withMissing}</strong>
        </article>
      </section>

      {/* <section className="panel reveal delay-1">
        <h2>Initial Charts</h2>
        <div className="chart-grid">
          <article className="chart-card">
            <h3>Status Distribution</h3>
            <div className="metric-row">
              <span>Completed</span>
              <div className="bar-track"><div className="bar-fill success" style={{ width: `${pct(chartStats.completed, chartStats.total)}%` }} /></div>
              <strong>{chartStats.completed}</strong>
            </div>
            <div className="metric-row">
              <span>Processing</span>
              <div className="bar-track"><div className="bar-fill warning" style={{ width: `${pct(chartStats.processing, chartStats.total)}%` }} /></div>
              <strong>{chartStats.processing}</strong>
            </div>
            <div className="metric-row">
              <span>Pending</span>
              <div className="bar-track"><div className="bar-fill neutral" style={{ width: `${pct(chartStats.pending, chartStats.total)}%` }} /></div>
              <strong>{chartStats.pending}</strong>
            </div>
            <div className="metric-row">
              <span>Failed</span>
              <div className="bar-track"><div className="bar-fill danger" style={{ width: `${pct(chartStats.failed, chartStats.total)}%` }} /></div>
              <strong>{chartStats.failed}</strong>
            </div>
          </article>

          <article className="chart-card">
            <h3>Score Bands</h3>
            <div className="metric-row">
              <span>High (75-100)</span>
              <div className="bar-track"><div className="bar-fill success" style={{ width: `${pct(chartStats.scoreHigh, chartStats.total)}%` }} /></div>
              <strong>{chartStats.scoreHigh}</strong>
            </div>
            <div className="metric-row">
              <span>Medium (50-74)</span>
              <div className="bar-track"><div className="bar-fill warning" style={{ width: `${pct(chartStats.scoreMedium, chartStats.total)}%` }} /></div>
              <strong>{chartStats.scoreMedium}</strong>
            </div>
            <div className="metric-row">
              <span>Low (0-49)</span>
              <div className="bar-track"><div className="bar-fill danger" style={{ width: `${pct(chartStats.scoreLow, chartStats.total)}%` }} /></div>
              <strong>{chartStats.scoreLow}</strong>
            </div>
          </article>
        </div>
      </section> */}

      <div className="candidate-layout reveal delay-2">
        <article className="panel">
          <h2>Tabular Output</h2>
          {loading && <p>Loading candidate records...</p>}
          {!loading && reportRows.length === 0 && <p>No candidate records available yet.</p>}

          {!loading && reportRows.length > 0 && (
            <div className="table-scroll">
              <table className="report-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Candidate</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Score</th>
                    <th>Missing Fields</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {reportRows.map((row) => (
                    <tr
                      key={row.id}
                      className={selectedCandidateId === row.id ? 'active-row' : ''}
                      onClick={() => selectCandidate(row.id)}
                    >
                      <td>{row.id}</td>
                      <td>{row.name}</td>
                      <td>{row.email}</td>
                      <td>{row.status}</td>
                      <td>{row.score ?? '—'}</td>
                      <td>{row.missingCount}</td>
                      <td>{row.uploadedAt ? new Date(row.uploadedAt).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <article className="panel">
          <h2>Personalized Draft Email</h2>
          {!selectedCandidate && <p>Select a candidate row to view draft email and missing-info profile.</p>}

          {selectedCandidate && details && (
            <div className="page-grid">
              <section className="info-box">
                <h3>{selectedCandidate.full_name || selectedCandidate.filename || `Candidate ${selectedCandidate.id}`}</h3>
                <p><strong>Missing Fields:</strong> {details.missingFields.join(', ') || 'No key fields missing'}</p>
                <div className="tag-row">
                  {details.education.detectedDegrees.map((degree) => (
                    <span className="tag" key={degree}>{degree}</span>
                  ))}
                  {details.research.topicHints.map((topic) => (
                    <span className="tag" key={topic}>{topic}</span>
                  ))}
                </div>
              </section>

              <section className="email-panel">
                <div className="email-toolbar">
                  <p className="muted">Ready-to-send draft</p>
                  <button type="button" className="btn compact" onClick={copyDraftEmail}>
                    {copied ? 'Copied' : 'Copy Email'}
                  </button>
                </div>
                <pre className="email-draft-pretty">{details.emailDraft}</pre>
              </section>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}

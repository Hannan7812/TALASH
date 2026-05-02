import { useEffect, useMemo, useState } from 'react';
import {
  detectMissingInformation,
  draftMissingInfoEmail,
  extractEducationSignals,
  extractExperienceSignals,
} from '../lib/profileParsers';
import {
  getCandidateAnalysis,
  getPublicationAnalysis,
  redraftCandidateEmail,
  runFullCandidateAnalysis,
  runPublicationAnalysis,
} from '../lib/api';

export default function CandidateInsightsPage({
  candidates,
  loading,
  candidatesError,
  selectedCandidate,
  selectedCandidateId,
  detailLoading,
  selectCandidate,
  onAnalyzeSelected,
  activeAnalyses,
  refreshCandidates,
}) {
  const selectedId = selectedCandidateId || selectedCandidate?.id;

  const [analysisStatus, setAnalysisStatus]       = useState('');
  const [storedAnalysis, setStoredAnalysis]       = useState(null);
  const [analysisLoading, setAnalysisLoading]     = useState(false);

  // Publication analysis state
  const [pubAnalysis, setPubAnalysis]             = useState(null);
  const [pubLoading, setPubLoading]               = useState(false);
  const [pubStatus, setPubStatus]                 = useState('');
  const [pubExpanded, setPubExpanded]             = useState(false);
  const [sortByTextLength, setSortByTextLength]   = useState(false);

  const education = useMemo(
    () => extractEducationSignals(selectedCandidate?.raw_text),
    [selectedCandidate?.raw_text],
  );
  const experience = useMemo(
    () => extractExperienceSignals(selectedCandidate?.raw_text),
    [selectedCandidate?.raw_text],
  );
  const missingFields = useMemo(
    () => detectMissingInformation(selectedCandidate, education),
    [selectedCandidate, education],
  );

  const displayedCandidates = useMemo(() => {
    if (!sortByTextLength) return candidates;

    return [...candidates].sort((a, b) => {
      const aLength = a.raw_text?.length || 0;
      const bLength = b.raw_text?.length || 0;
      return bLength - aLength;
    });
  }, [candidates, sortByTextLength]);

  const resolvedMissingFields = storedAnalysis?.missing_fields?.length
    ? storedAnalysis.missing_fields
    : missingFields;

  const resolvedEmailDraft = storedAnalysis?.draft_email?.trim()
    ? storedAnalysis.draft_email
    : draftMissingInfoEmail(selectedCandidate, resolvedMissingFields);

  // Load stored analysis whenever a candidate is selected
  useEffect(() => {
    async function loadStoredAnalysis() {
      if (!selectedCandidate?.id) {
        setStoredAnalysis(null);
        return;
      }
      setAnalysisLoading(true);
      try {
        const analysis = await getCandidateAnalysis(selectedCandidate.id);
        setStoredAnalysis(analysis);
      } catch {
        setStoredAnalysis(null);
      } finally {
        setAnalysisLoading(false);
      }
    }
    loadStoredAnalysis();
  }, [selectedCandidate?.id]);

  // Load cached publication analysis whenever a candidate is selected
  useEffect(() => {
    async function loadPubAnalysis() {
      if (!selectedCandidate?.id) {
        setPubAnalysis(null);
        return;
      }
      setPubLoading(true);
      try {
        const result = await getPublicationAnalysis(selectedCandidate.id);
        if (result?.is_analysed) {
          setPubAnalysis(result);
        } else {
          setPubAnalysis(null);
        }
      } catch {
        setPubAnalysis(null);
      } finally {
        setPubLoading(false);
      }
    }
    loadPubAnalysis();
  }, [selectedCandidate?.id]);

  async function handleRunFullAnalysis() {
    if (!selectedCandidate?.id) return;
    setAnalysisStatus('Running full backend analysis (education, experience, research, missing info)...');
    try {
      await runFullCandidateAnalysis(selectedCandidate.id);
      const analysis = await getCandidateAnalysis(selectedCandidate.id);
      setStoredAnalysis(analysis);
      setAnalysisStatus('Full backend analysis completed and loaded.');
    } catch (error) {
      setAnalysisStatus(error.message || 'Failed to run full backend analysis.');
    }
  }

  async function handleRedraftEmail() {
    if (!selectedCandidate?.id) return;
    setAnalysisStatus('Generating personalized draft email from backend...');
    try {
      await redraftCandidateEmail(selectedCandidate.id);
      const analysis = await getCandidateAnalysis(selectedCandidate.id);
      setStoredAnalysis(analysis);
      setAnalysisStatus('Draft email refreshed from backend analysis.');
    } catch (error) {
      setAnalysisStatus(error.message || 'Failed to redraft email.');
    }
  }

  async function handleRunPublicationAnalysis() {
    if (!selectedCandidate?.id) return;
    setPubStatus('Running deep publication analysis using dedicated LLM (this may take 10–30 seconds)...');
    setPubLoading(true);
    try {
      const result = await runPublicationAnalysis(selectedCandidate.id);
      // Reload the cached version for display
      const cached = await getPublicationAnalysis(selectedCandidate.id);
      setPubAnalysis(cached);
      setPubStatus(
        `Publication analysis complete. ` +
        `${result.publications_inserted} publication(s) extracted and saved to database.`,
      );
      setPubExpanded(true);
    } catch (error) {
      setPubStatus('Publication analysis failed.');
    } finally {
      setPubLoading(false);
    }
  }

  // ---- Render helpers ----

  function renderIndexingBadges(journal, conference) {
    const badges = [];
    if (journal?.is_wos_indexed)      badges.push({ label: 'WoS',    color: '#2196f3' });
    if (journal?.is_scopus_indexed || conference?.is_scopus_indexed)
                                       badges.push({ label: 'Scopus', color: '#4caf50' });
    if (conference?.is_ieee_xplore)   badges.push({ label: 'IEEE',   color: '#00bcd4' });
    if (conference?.is_springer)      badges.push({ label: 'Springer', color: '#ff9800' });
    if (conference?.is_acm)           badges.push({ label: 'ACM',    color: '#9c27b0' });
    if (journal?.is_predatory)        badges.push({ label: '⚠ Predatory', color: '#f44336' });
    if (!badges.length)               return null;
    return (
      <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap', marginLeft: 6 }}>
        {badges.map((b) => (
          <span key={b.label} style={{
            background: b.color, color: '#fff', padding: '1px 7px',
            borderRadius: 10, fontSize: '0.7rem', fontWeight: 700,
          }}>{b.label}</span>
        ))}
      </span>
    );
  }

  const pubSummary  = pubAnalysis?.cached_analysis?.summary || {};
  const publications = pubAnalysis?.cached_analysis?.publications || [];
  const coauthor    = pubAnalysis?.coauthor_analysis || {};
  const topic       = pubAnalysis?.topic_variability || {};

  return (
    <section className="page-grid">
      {/* <section className="summary-strip reveal">
        <article className="summary-tile">
          <p>Total Candidates</p>
          <strong>{candidates.length}</strong>
        </article>
        <article className="summary-tile">
          <p>Analyzed</p>
          <strong>{candidates.filter((item) => item.status === 'completed').length}</strong>
        </article>
        <article className="summary-tile">
          <p>Pending/Processing</p>
          <strong>{candidates.filter((item) => item.status !== 'completed').length}</strong>
        </article>
      </section> */}

      <div className="candidate-layout reveal delay-1">
        <article className="panel">
          <h2>Candidates</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn" onClick={refreshCandidates}>Refresh</button>
            <button
              type="button"
              className="btn"
              onClick={() => setSortByTextLength((value) => !value)}
            >
              {sortByTextLength ? 'Show Original Order' : 'Sort by Rank'}
            </button>
          </div>

          {loading && <p>Loading candidates...</p>}
          {candidatesError && <p className="error-text">{candidatesError}</p>}
          {!loading && candidates.length === 0 && <p>No parsed candidates found yet.</p>}

          <ul className="candidate-list">
            {displayedCandidates.map((candidate) => (
              <li
                key={candidate.id}
                className={`candidate-item ${selectedId === candidate.id ? 'selected' : ''}`}
                onClick={() => selectCandidate(candidate.id)}
              >
                <strong>{candidate.full_name || candidate.filename}</strong>
                <div className="muted small-text">
                  {candidate.filename}
                  <br />
                  Status: {candidate.status}
                  {activeAnalyses[candidate.id] && <span className="busy-tag"> (Processing...)</span>}
                </div>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          {detailLoading && <p>Loading candidate details...</p>}
          {!selectedCandidate && !detailLoading && (
            <div className="empty-insight">
              <h3>Select a candidate to open organized insights</h3>
              <p className="muted">Once selected, this area shows all sections in one place: education, research, experience, publications, and missing information draft.</p>
              <div className="insight-grid">
                <article className="placeholder-card">
                  <h4>Education</h4>
                  <p className="muted small-text">Degrees, score/CGPA hints, school-to-university continuity, and gap windows.</p>
                </article>
                <article className="placeholder-card">
                  <h4>Publication Analysis</h4>
                  <p className="muted small-text">Deep LLM extraction of publications, impact factors, indexing, co-authors, and topic diversity.</p>
                </article>
                <article className="placeholder-card">
                  <h4>Experience</h4>
                  <p className="muted small-text">Employment timeline markers plus teaching and industry indicators.</p>
                </article>
                <article className="placeholder-card">
                  <h4>Missing Information</h4>
                  <p className="muted small-text">Auto-detected missing profile fields with personalized email draft.</p>
                </article>
              </div>
            </div>
          )}

          {selectedCandidate && !detailLoading && (
            <div className="page-grid">

              {/* ---- Profile Summary ---- */}
              <section className="info-box">
                <h3>Profile Summary</h3>
                <p><strong>Name:</strong> {selectedCandidate.full_name || '—'}</p>
                <p><strong>Email:</strong> {selectedCandidate.email || '—'}</p>
                {/* <p><strong>Phone:</strong> {selectedCandidate.phone || '—'}</p>
                <p><strong>LinkedIn:</strong> {selectedCandidate.linkedin_url || '—'}</p> */}
                <p><strong>Summary:</strong> {selectedCandidate.overall_summary || 'Not generated yet.'}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                  <button type="button" className="btn" onClick={onAnalyzeSelected} disabled={activeAnalyses[selectedCandidate.id]}>
                    {activeAnalyses[selectedCandidate.id] ? 'Analyzing...' : 'LLM Analysis'}
                  </button>
                  {/* <button type="button" className="btn" onClick={handlePreprocessSelected}>
                    Structured Preprocessing
                  </button> */}
                  <button type="button" className="btn" onClick={handleRunFullAnalysis}>
                    Education Analysis
                  </button>
                  <button type="button" className="btn" onClick={handleRedraftEmail}>
                    Write Email with AI
                  </button>
                </div>
                {analysisLoading && <p className="status-spacing small-text">Loading stored backend analysis...</p>}
                {analysisStatus && <p className="status-spacing small-text">{analysisStatus}</p>}
              </section>

              {/* ---- Education ---- */}
              <section className="info-box">
                <h3>Education</h3>
                <p><strong>Heursitic Degrees:</strong> {education.detectedDegrees.join(', ') || 'None detected'}</p>
                <p>
                  <strong>Heuristic Universities:</strong> {selectedCandidate.universities || 'None detected'}
                  
                  {/* Handle multiple QS rankings - only show available ones */}
                  {storedAnalysis?.education?.qs_rankings?.length > 0 && storedAnalysis.education.qs_rankings.some(qs => qs.available) && (
                    <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {storedAnalysis.education.qs_rankings.filter(qs => qs.available).map((qs, idx) => (
                        <span key={idx} className="qs-badge" style={{
                          padding: '3px 10px', 
                          background: '#f5a623', 
                          color: '#fff', 
                          borderRadius: 12, 
                          fontSize: '0.85em'
                        }}>
                          {qs.searched_university}: QS Rank: {qs.qs_ranking} ({qs.matched_institution})
                        </span>
                      ))}
                    </div>
                  )}
                </p>
                {/* <p><strong>School Data:</strong> {education.hasSchoolData ? 'Yes' : 'No'}</p> */}
                {/* <p><strong>University Data:</strong> {education.hasUniversityData ? 'Yes' : 'No'}</p> */}
                {/* <p><strong>Score/CGPA Data:</strong> {education.hasScoreData ? 'Yes' : 'No'}</p> */}
                {/* <p><strong>Potential Gaps:</strong> {education.gapHints.join(' | ') || 'No major gaps detected'}</p> */}
              </section>

              {/* ================================================================
                  PUBLICATION ANALYSIS SECTION
                  ================================================================ */}
              <section className="info-box" style={{ gridColumn: '1 / -1' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
                  <h3 style={{ margin: 0 }}>
                    Publication Analysis
                    {/* <span style={{
                      marginLeft: 10, padding: '2px 10px', background: '#b45309',
                      color: '#fff', borderRadius: 10, fontSize: '0.72rem', fontWeight: 700,
                    }}></span> */}
                  </h3>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    {/* {pubAnalysis && (
                      <button
                        type="button"
                        className="btn compact"
                        onClick={() => setPubExpanded((v) => !v)}
                        style={{ fontSize: '0.82rem' }}
                      >
                        {pubExpanded ? 'Collapse ▲' : 'Expand ▼'}
                      </button>
                    )} */}
                    <button
                      type="button"
                      className="btn compact"
                      onClick={handleRunPublicationAnalysis}
                      disabled={pubLoading}
                    >
                      {pubLoading ? 'Analysing Publications...' : pubAnalysis ? 'Run Publication Analysis' : 'Run Deep Publication Analysis'}
                    </button>
                  </div>
                </div>

                {pubStatus && (
                  <p className={`small-text ${pubStatus.toLowerCase().includes('fail') ? 'error-text' : 'success-text'}`}
                     style={{ marginTop: 8 }}>
                    {pubStatus}
                  </p>
                )}

                {pubLoading && !pubAnalysis && (
                  <p className="muted small-text" style={{ marginTop: 8 }}>
                    Contacting deep analysis LLM... Please wait.
                  </p>
                )}

                {!pubAnalysis && !pubLoading && (
                  <p className="muted small-text" style={{ marginTop: 8 }}>
                    No publication analysis run yet. Click "Run Deep Publication Analysis" to extract and analyse all publications from this CV using the dedicated research LLM.
                  </p>
                )}

                {pubAnalysis && (
                  <>
                    {/* Summary bar */}
                    <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 14 }}>
                      {[
                        { label: 'Total Publications', value: pubSummary.total_publications ?? pubAnalysis.publications_count },
                        { label: 'Journals',           value: pubSummary.journal_count },
                        { label: 'Conferences',        value: pubSummary.conference_count },
                        { label: 'Avg Impact Factor',  value: pubSummary.avg_impact_factor != null ? pubSummary.avg_impact_factor.toFixed(2) : '—' },
                        { label: 'Max Impact Factor',  value: pubSummary.max_impact_factor != null ? pubSummary.max_impact_factor.toFixed(2) : '—' },
                        { label: 'WoS Indexed',        value: pubSummary.wos_indexed_count ?? '—' },
                        { label: 'Scopus Indexed',     value: pubSummary.scopus_indexed_count ?? '—' },
                      ].map(({ label, value }) => (
                        <div key={label} style={{
                          background: 'var(--panel)', padding: '8px 14px',
                          borderRadius: 10, minWidth: 110, textAlign: 'center', border: '1px solid #e9ddcf',
                        }}>
                          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#b45309' }}>{value ?? '—'}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--muted, #888)', marginTop: 2 }}>{label}</div>
                        </div>
                      ))}
                    </div>

                    {pubExpanded && (
                      <>
                        {/* Co-author Analysis */}
                        {coauthor && Object.keys(coauthor).length > 0 && (
                          <div style={{ marginTop: 18 }}>
                            {/* <h4 style={{ marginBottom: 8 }}>Co-authorship Profile</h4> */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
                              {/* <p><strong>Unique Co-authors:</strong> {coauthor.total_unique_coauthors ?? '—'}</p>
                              <p><strong>Avg Co-authors/Paper:</strong> {coauthor.avg_coauthors_per_paper != null ? Number(coauthor.avg_coauthors_per_paper).toFixed(1) : '—'}</p>
                              <p><strong>Most Frequent Collaborator:</strong> {coauthor.most_frequent_collaborator || '—'}</p>
                              <p><strong>Diversity Score:</strong> {coauthor.collaboration_diversity_score != null ? Number(coauthor.collaboration_diversity_score).toFixed(2) : '—'}</p>
                              <p><strong>International Collaborations:</strong> {coauthor.has_international_collaborations === true ? '✓ Yes' : coauthor.has_international_collaborations === false ? '✗ No' : '—'}</p>
                              <p><strong>Student Collaborations:</strong> {coauthor.has_student_collaborations === true ? '✓ Yes' : coauthor.has_student_collaborations === false ? '✗ No' : '—'}</p> */}
                            </div>
                            {coauthor.collaboration_summary && (
                              <p style={{ marginTop: 8, fontStyle: 'italic', color: 'var(--muted, #888)', fontSize: '0.88rem' }}>
                                {coauthor.collaboration_summary}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Topic Variability */}
                        {topic && Object.keys(topic).length > 0 && (
                          <div style={{ marginTop: 18 }}>
                            <h4 style={{ marginBottom: 8 }}>Research Topic Profile</h4>
                            <p><strong>Dominant Topic:</strong> {topic.dominant_topic || '—'}</p>
                            <p><strong>Diversity Score:</strong> {topic.diversity_score != null ? Number(topic.diversity_score).toFixed(2) : '—'} / 1.0</p>
                            <p><strong>Topic Trend:</strong> {topic.topic_trend || '—'}</p>
                            {topic.topic_clusters && (
                              <p><strong>Topic Clusters:</strong> {
                                Array.isArray(topic.topic_clusters)
                                  ? topic.topic_clusters.join(' · ')
                                  : JSON.stringify(topic.topic_clusters)
                              }</p>
                            )}
                            {topic.variability_summary && (
                              <p style={{ marginTop: 6, fontStyle: 'italic', color: 'var(--muted, #888)', fontSize: '0.88rem' }}>
                                {topic.variability_summary}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Publications Table */}
                        {publications.length > 0 && (
                          <div style={{ marginTop: 18 }}>
                            <h4 style={{ marginBottom: 8 }}>Publications ({publications.length})</h4>
                            <div style={{ overflowX: 'auto' }}>
                              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                                <thead>
                                  <tr style={{ background: '#fff5ea', textAlign: 'left', borderBottom: '2px solid #e9ddcf' }}>
                                    <th style={{ padding: '6px 10px' }}>#</th>
                                    <th style={{ padding: '6px 10px' }}>Title</th>
                                    <th style={{ padding: '6px 10px' }}>Type</th>
                                    <th style={{ padding: '6px 10px' }}>Year</th>
                                    <th style={{ padding: '6px 10px' }}>Venue / IF</th>
                                    <th style={{ padding: '6px 10px' }}>Position</th>
                                    {/* <th style={{ padding: '6px 10px' }}>Indexing</th> */}
                                  </tr>
                                </thead>
                                <tbody>
                                  {publications.map((pub, idx) => {
                                    const j = pub.journal || {};
                                    const c = pub.conference || {};
                                    const venue = pub.pub_type === 'journal'
                                      ? j.journal_name || '—'
                                      : c.conference_name || '—';
                                    const ifLabel = j.impact_factor != null
                                      ? `IF: ${Number(j.impact_factor).toFixed(2)}`
                                      : c.core_rank
                                        ? `CORE: ${c.core_rank}`
                                        : '';
                                    return (
                                      <tr key={idx} style={{ borderTop: '1px solid var(--line, #e9ddcf)' }}>
                                        <td style={{ padding: '5px 10px', color: 'var(--muted)' }}>{idx + 1}</td>
                                        <td style={{ padding: '5px 10px', maxWidth: 300 }}>{pub.title || '—'}</td>
                                        <td style={{ padding: '5px 10px' }}>
                                          <span style={{
                                            background: pub.pub_type === 'journal' ? '#1976d2' : '#388e3c',
                                            color: '#fff', padding: '1px 7px', borderRadius: 8, fontSize: '0.72rem',
                                          }}>
                                            {pub.pub_type || '—'}
                                          </span>
                                        </td>
                                        <td style={{ padding: '5px 10px' }}>{pub.year || '—'}</td>
                                        <td style={{ padding: '5px 10px' }}>
                                          <span>{venue}</span>
                                          {ifLabel && <span style={{ marginLeft: 6, color: '#b45309', fontSize: '0.78rem', fontWeight: 700 }}>{ifLabel}</span>}
                                        </td>
                                        {/* <td style={{ padding: '5px 10px' }}>
                                          {pub.candidate_author_position != null
                                            ? `#${pub.candidate_author_position}`
                                            : '—'}
                                        </td> */}
                                        <td style={{ padding: '5px 10px' }}>
                                          {renderIndexingBadges(j, c) || <span style={{ color: 'var(--muted)' }}>—</span>}
                                        </td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </>
                )}
              </section>
              {/* ================================================================ */}

              {/* ---- Experience & Skills ---- */}
              {/* <section className="info-box">
                <h3>Experience and Skills</h3>
                <p><strong>Employment Evidence:</strong> {experience.hasEmploymentEvidence ? 'Yes' : 'No'}</p>
                <p><strong>Teaching Evidence:</strong> {experience.hasTeachingEvidence ? 'Yes' : 'No'}</p>
                <p><strong>Industry Evidence:</strong> {experience.hasIndustryEvidence ? 'Yes' : 'No'}</p>
                <p><strong>Timeline Years:</strong> {experience.timelineHints.join(', ') || 'None detected'}</p>
                {!!storedAnalysis?.experience?.timeline_checks && (
                  <>
                    <p><strong>Education-Employment Overlaps:</strong> {storedAnalysis.experience.timeline_checks.education_employment_overlaps?.length || 0}</p>
                    <p><strong>Job-Job Overlaps:</strong> {storedAnalysis.experience.timeline_checks.job_overlaps?.length || 0}</p>
                    <p><strong>Professional Gaps:</strong> {storedAnalysis.experience.timeline_checks.professional_gaps?.length || 0}</p>
                    <p><strong>Progression Signal:</strong> {storedAnalysis.experience.timeline_checks.progression_signal || 'n/a'}</p>
                  </>
                )}
              </section> */}

              {/* ---- Missing Information ---- */}
              <section className="info-box">
                <h3>Missing Information</h3>
                <p><strong>Missing Fields:</strong> {resolvedMissingFields.join(', ') || 'No key fields missing'}</p>
                {resolvedMissingFields.length > 0 && (
                  <pre className="email-draft">{resolvedEmailDraft}</pre>
                )}
              </section>

              {/* ---- Raw Text ---- */}
              <section className="raw-box">
                <h3>Raw Parsed Text</h3>
                <p>{selectedCandidate.raw_text || 'No raw text available.'}</p>
              </section>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
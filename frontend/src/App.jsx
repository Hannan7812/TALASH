import { useEffect, useMemo, useRef, useState } from 'react';
import './App.css';
import { analyzeCandidate, getCandidateById, listCandidates } from './lib/api';
import OverviewPage from './pages/OverviewPage';
import IngestionPage from './pages/IngestionPage';
import CandidateInsightsPage from './pages/CandidateInsightsPage';
import AnalyticsReportsPage from './pages/AnalyticsReportsPage';
import { Toaster } from 'react-hot-toast';

const ROUTES = [
  {
    id: 'pulse',
    label: 'Home',
    title: 'Workspace Home',
    description:
      'A consolidated launch point that surfaces the current dataset volume, processing state, export readiness, and the fastest actions for keeping the workflow moving without leaving the dashboard.',
    component: OverviewPage,
  },
  {
    id: 'dropzone',
    label: 'Document Dropzone',
    title: 'Multi-Path Document Intake',
    description:
      'Bring new candidate files into the system through individual uploads, batch selection, local folder capture, combined PDF splitting, or backend-side filename parsing with immediate feedback after each import path.',
    component: IngestionPage,
  },
  {
    id: 'atlas',
    label: 'Profile',
    title: 'Candidate Intelligence',
    description:
      'Open a selected profile to inspect the extracted education trail, career progression, publication signals, missing-data notes, and backend analysis output in a single structured view.',
    component: CandidateInsightsPage,
  },
  // {
  //   id: 'ledger',
  //   label: 'Insight Ledger',
  //   title: 'Operational Reporting Ledger',
  //   description:
  //     'Review the candidate register, compare processing states, inspect score bands, and copy polished follow-up messages generated from the currently selected profile.',
  //   component: AnalyticsReportsPage,
  // },
];

function readHashRoute() {
  const raw = window.location.hash.replace('#/', '');
  return ROUTES.some((route) => route.id === raw) ? raw : ROUTES[0].id;
}

async function loadCandidatesList({
  setLoadingCandidates,
  setCandidatesError,
  setCandidates,
  selectedCandidateId,
  setSelectedCandidateId,
  setSelectedCandidate,
}) {
  setLoadingCandidates(true);
  setCandidatesError('');

  try {
    const items = await listCandidates();
    setCandidates(items);

    if (selectedCandidateId && !items.some((candidate) => candidate.id === selectedCandidateId)) {
      setSelectedCandidateId(null);
      setSelectedCandidate(null);
    }
  } catch (error) {
    setCandidatesError(error.message || 'Failed to fetch candidate records');
  } finally {
    setLoadingCandidates(false);
  }
}

function App() {
  const [activeRoute, setActiveRoute] = useState(readHashRoute);
  const [candidates, setCandidates] = useState([]);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [candidatesError, setCandidatesError] = useState('');

  const [selectedCandidateId, setSelectedCandidateId] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [activeAnalyses, setActiveAnalyses] = useState({});
  const selectedCandidateIdRef = useRef(selectedCandidateId);

  useEffect(() => {
    selectedCandidateIdRef.current = selectedCandidateId;
  }, [selectedCandidateId]);

  const activeRouteMeta = useMemo(
    () => ROUTES.find((route) => route.id === activeRoute) || ROUTES[0],
    [activeRoute],
  );

  const ActivePage = activeRouteMeta.component;

  useEffect(() => {
    const handleHashChange = () => {
      setActiveRoute(readHashRoute());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, []);

  useEffect(() => {
    void loadCandidatesList({
      setLoadingCandidates,
      setCandidatesError,
      setCandidates,
      selectedCandidateId: selectedCandidateIdRef.current,
      setSelectedCandidateId,
      setSelectedCandidate,
    });
  }, []);

  async function refreshCandidates() {
    await loadCandidatesList({
      setLoadingCandidates,
      setCandidatesError,
      setCandidates,
      selectedCandidateId: selectedCandidateIdRef.current,
      setSelectedCandidateId,
      setSelectedCandidate,
    });
  }

  async function selectCandidate(candidateId) {
    setSelectedCandidateId(candidateId);
    setLoadingDetails(true);

    try {
      const details = await getCandidateById(candidateId);
      setSelectedCandidate(details);
    } catch (error) {
      setCandidatesError(error.message || 'Failed to load candidate details');
      setSelectedCandidate(null);
    } finally {
      setLoadingDetails(false);
    }
  }

  async function runAnalysisForSelectedCandidate() {
    if (!selectedCandidateId) {
      return;
    }

    setActiveAnalyses((prev) => ({ ...prev, [selectedCandidateId]: true }));

    try {
      await analyzeCandidate(selectedCandidateId);
      await refreshCandidates();
      await selectCandidate(selectedCandidateId);
    } catch (error) {
      setCandidatesError(error.message || 'Failed to analyze candidate');
    } finally {
      setActiveAnalyses((prev) => ({ ...prev, [selectedCandidateId]: false }));
    }
  }

  function navigate(routeId) {
    window.history.pushState({}, '', `#/${routeId}`);
    setActiveRoute(routeId);
  }

  return (
    <div className="app-shell">
      <header className="topbar reveal">
        <div className="brand-block">
          <div className="brand-mark">T</div>
          <div>
            <h1>TALASH</h1>
          </div>
        </div>

      </header>

      <div className="workspace-frame">
        <aside className="route-rail reveal delay-1">
          {/* <p className="rail-heading">Workspace</p> */}
          <nav className="nav-list" aria-label="Main navigation">
            {ROUTES.map((route) => (
              <button
                key={route.id}
                type="button"
                className={`nav-item ${activeRoute === route.id ? 'active' : ''}`}
                onClick={() => navigate(route.id)}
              >
                <span>{route.label}</span>
                <span className="nav-item-arrow">↗</span>
              </button>
            ))}
          </nav>

          {/* <div className="rail-note">
            <p className="muted small-text">Fast-switch between ingestion, candidate review, and reporting without changing the workflow underneath.</p>
          </div> */}
        </aside>

        <main className="content">
          <section className="page-header reveal">
            <div className="page-header-top">
              <div>
                  <p className="section-label">Active workspace</p>
                <h2>{activeRouteMeta.title}</h2>
              </div>
              <button type="button" className="btn compact ghost" onClick={refreshCandidates}>
                Refresh data
              </button>
            </div>
            <p>{activeRouteMeta.description}</p>
            {candidatesError && <p className="error-text">{candidatesError}</p>}
          </section>

          <section className="page-surface reveal delay-2">
            <ActivePage
              candidates={candidates}
              loading={loadingCandidates}
              refreshCandidates={refreshCandidates}
              selectedCandidate={selectedCandidate}
              selectedCandidateId={selectedCandidateId}
              detailLoading={loadingDetails}
              selectCandidate={selectCandidate}
              onAnalyzeSelected={runAnalysisForSelectedCandidate}
              activeAnalyses={activeAnalyses}
              candidatesError={candidatesError}
              onUploaded={refreshCandidates}
            />
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;

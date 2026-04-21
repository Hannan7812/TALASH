const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload?.detail
        ? payload.detail
        : typeof payload === 'string' && payload
          ? payload
          : 'Request failed';
    throw new Error(detail);
  }

  return payload;
}

export async function listCandidates() {
  const response = await fetch(`${API_BASE_URL}/cv/candidates`);
  const payload = await parseResponse(response);
  return payload?.candidates || [];
}

export async function getCandidateById(candidateId) {
  const response = await fetch(`${API_BASE_URL}/cv/candidate/${candidateId}`);
  return parseResponse(response);
}

export async function uploadCandidateCV(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/cv/upload`, {
    method: 'POST',
    body: formData,
  });

  return parseResponse(response);
}

export async function uploadCandidateCVBulk(files) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await fetch(`${API_BASE_URL}/cv/upload/bulk`, {
    method: 'POST',
    body: formData,
  });

  return parseResponse(response);
}

/**
 * Upload a single combined PDF that contains multiple CVs separated by blank pages.
 * The backend splits it and ingests each segment as a separate candidate.
 */
export async function uploadCombinedBulkPDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/cv/upload/bulk-combined`, {
    method: 'POST',
    body: formData,
  });

  return parseResponse(response);
}

export async function ingestCandidateFolder(folderPath, deleteAfterParse = false) {
  const params = new URLSearchParams({
    folder_path: folderPath,
    delete_after_parse: String(deleteAfterParse),
  });

  const response = await fetch(`${API_BASE_URL}/cv/ingest/folder?${params.toString()}`, {
    method: 'POST',
  });

  return parseResponse(response);
}

export async function analyzeCandidate(candidateId) {
  const response = await fetch(`${API_BASE_URL}/cv/candidate/${candidateId}/analyze`, {
    method: 'POST',
  });

  return parseResponse(response);
}

export async function parseCandidateByFilename(filename) {
  const params = new URLSearchParams({ filename });
  const response = await fetch(`${API_BASE_URL}/cv/parse?${params.toString()}`, {
    method: 'POST',
  });

  return parseResponse(response);
}

export async function preprocessCandidate(candidateId) {
  const response = await fetch(`${API_BASE_URL}/cv/candidate/${candidateId}/preprocess`, {
    method: 'POST',
  });

  return parseResponse(response);
}

export async function exportStructuredDataset() {
  const response = await fetch(`${API_BASE_URL}/cv/preprocess/export`, {
    method: 'POST',
  });

  return parseResponse(response);
}

export async function runFullCandidateAnalysis(candidateId) {
  const response = await fetch(`${API_BASE_URL}/analysis/candidate/${candidateId}/full`, {
    method: 'POST',
  });

  return parseResponse(response);
}

export async function getCandidateAnalysis(candidateId) {
  const response = await fetch(`${API_BASE_URL}/analysis/candidate/${candidateId}`);
  return parseResponse(response);
}

export async function redraftCandidateEmail(candidateId) {
  const response = await fetch(`${API_BASE_URL}/analysis/candidate/${candidateId}/email`, {
    method: 'POST',
  });

  return parseResponse(response);
}

/**
 * Run deep LLM publication analysis for a candidate using the dedicated second Groq key.
 * Fills publications, journal_details, conference_details, coauthor_analysis, topic_variability tables.
 */
export async function runPublicationAnalysis(candidateId) {
  const response = await fetch(`${API_BASE_URL}/analysis/candidate/${candidateId}/publications`, {
    method: 'POST',
  });

  return parseResponse(response);
}

/**
 * Fetch cached deep publication analysis results for a candidate.
 */
export async function getPublicationAnalysis(candidateId) {
  const response = await fetch(`${API_BASE_URL}/analysis/candidate/${candidateId}/publications`);
  return parseResponse(response);
}

export { API_BASE_URL };
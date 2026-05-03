function normalizeWhitespace(text) {
  return (text || '').replace(/\s+/g, ' ').trim();
}

function hasAny(text, terms) {
  return terms.some((term) => {
    if (term instanceof RegExp) {
      return term.test(text);
    }
    const lower = text.toLowerCase();
    return lower.includes(term.toLowerCase());
  });
}

export function extractEducationSignals(rawText) {
  const cleaned = normalizeWhitespace(rawText);
  if (!cleaned) {
    return {
      detectedDegrees: [],
      hasSchoolData: false,
      hasUniversityData: false,
      hasScoreData: false,
      gapHints: [],
    };
  }

  const degrees = [];
  const checks = [
    ['SSE/Matric', [/\bsse\b/i, /\bmatric\b/i]],
    ['HSSC/Intermediate', [/\bhssc\b/i, /\bintermediate\b/i, /\bf\.?sc\b/i]],
    ['BS/BSc', [/\bbs\b/i, /\bb\.?s\.?\b/i, /\bbsc\b/i, /\bb\.sc\b/i, /\bbachelors?\b/i]],
    ['MS/MPhil', [/\bms\b/i, /\bm\.?s\.?\b/i, /\bmphil\b/i, /\bm\.phil\b/i, /\bmasters?\b/i]],
    ['PhD', [/\bphd\b/i, /\bph\.?d\.?\b/i]],
  ];

  checks.forEach(([label, terms]) => {
    if (hasAny(cleaned, terms)) {
      degrees.push(label);
    }
  });

  const yearMatches = cleaned.match(/\b(19|20)\d{2}\b/g) || [];
  const years = yearMatches.map((value) => Number(value)).sort((a, b) => a - b);
  const gapHints = [];

  for (let index = 1; index < years.length; index += 1) {
    const gap = years[index] - years[index - 1];
    if (gap >= 3) {
      gapHints.push(`${years[index - 1]}-${years[index]} (${gap} years)`);
    }
  }

  // Attempt to extract university names
  const uniRegex = /([A-Z][a-z0-9-]*\s+(?:(?:of|and|the|for|at|in|&|\-)\s+)*)*(?:University|Institute|College)(?:\s+(?:(?:of|and|the|for|at|in|&|\-)\s+)*[A-Z][a-z0-9-]*){0,4}/g;
  const uniMatches = rawText.match(uniRegex) || [];
  
  const detectedUniversities = [...new Set(
    uniMatches.map(u => {
      let cleaned = u.trim().replace(/[\s\n\r]+/g, ' ');
      
      // Remove common prefix noise that gets swept up in caps matching
      while (/^(Education|Experience|School|References|Name|Address|Contact|Email|Date|Phone|Profile|Summary|Objective|Skills|Projects|Abubakar-rashid|Abubakar|Rashid|Islamabad)\s+/i.test(cleaned)) {
        cleaned = cleaned.replace(/^(Education|Experience|School|References|Name|Address|Contact|Email|Date|Phone|Profile|Summary|Objective|Skills|Projects|Abubakar-rashid|Abubakar|Rashid|Islamabad)\s+/i, '').trim();
      }

      // Remove common suffix noise
      cleaned = cleaned.replace(/\s+(Islamabad|Lahore|Karachi|Rawalpindi|Pakistan|H-12|Sector|Phase|Road|Street|City)$/i, '').trim();
      
      return cleaned;
    })
  )].filter(Boolean);

  return {
    detectedDegrees: degrees,
    detectedUniversities,
    hasSchoolData: hasAny(cleaned, ['sse', 'hssc', 'matric', 'intermediate']),
    hasUniversityData: hasAny(cleaned, ['university', 'institute', 'college']),
    hasScoreData: /\b\d{1,2}(\.\d{1,2})?\s*(cgpa|gpa)\b|\b\d{2,3}%\b/i.test(cleaned),
    gapHints,
  };
}

export function extractResearchSignals(rawText) {
  const cleaned = normalizeWhitespace(rawText);
  if (!cleaned) {
    return {
      publicationHints: 0,
      indexingHints: [],
      collaborationHints: [],
      topicHints: [],
    };
  }

  const publicationHints = (cleaned.match(/journal|conference|publication|proceedings/gi) || []).length;
  const indexingHints = ['scopus', 'web of science', 'wos', 'ieee', 'acm', 'springer', 'q1', 'q2', 'q3', 'q4']
    .filter((term) => cleaned.toLowerCase().includes(term));

  const collaborationHints = ['co-author', 'collaboration', 'supervisor', 'co-supervisor']
    .filter((term) => cleaned.toLowerCase().includes(term));

  const topicLexicon = ['nlp', 'machine learning', 'deep learning', 'computer vision', 'software engineering', 'cybersecurity', 'data mining'];
  const topicHints = topicLexicon.filter((topic) => cleaned.toLowerCase().includes(topic));

  return {
    publicationHints,
    indexingHints,
    collaborationHints,
    topicHints,
  };
}

export function extractExperienceSignals(rawText) {
  const cleaned = normalizeWhitespace(rawText);
  if (!cleaned) {
    return {
      hasEmploymentEvidence: false,
      hasTeachingEvidence: false,
      hasIndustryEvidence: false,
      timelineHints: [],
    };
  }

  const years = (cleaned.match(/\b(19|20)\d{2}\b/g) || []).map((v) => Number(v));
  const uniqueYears = [...new Set(years)].sort((a, b) => a - b);

  return {
    hasEmploymentEvidence: hasAny(cleaned, ['experience', 'employment', 'worked', 'position', 'role']),
    hasTeachingEvidence: hasAny(cleaned, ['lecturer', 'assistant professor', 'teaching', 'instructor']),
    hasIndustryEvidence: hasAny(cleaned, ['engineer', 'developer', 'consultant', 'manager', 'analyst']),
    timelineHints: uniqueYears.slice(0, 8),
  };
}

export function detectMissingInformation(candidate, education) {
  const missing = [];

  if (!candidate?.full_name) missing.push('full name');
  if (!candidate?.email) missing.push('email address');
  if (!candidate?.phone) missing.push('phone number');
  if (!candidate?.nationality) missing.push('nationality');

  const rawText = normalizeWhitespace(candidate?.raw_text);
  if (!/\b(19|20)\d{2}\b/.test(rawText)) missing.push('clear education/employment dates');
  if (!/journal|conference|publication/i.test(rawText)) missing.push('publication details');

  // Add education-related missing information
  if (education) {
    if (!education.hasScoreData) missing.push('GPA/CGPA information');
  }

  return missing;
}

export function draftMissingInfoEmail(candidate, missingFields) {
  const candidateName = candidate?.full_name || 'Candidate';
  const list = missingFields.map((item) => `- ${item}`).join('\n');

  return `Subject: Request for Additional Information - TALASH Profile Review\n\nDear ${candidateName},\n\nThank you for sharing your profile. While reviewing your CV in TALASH, we noticed a few details that are required for a complete evaluation:\n\n${list}\n\nPlease share these details (or an updated CV) so we can complete your educational, research, and experience analysis fairly.\n\nBest regards,\nTALASH Recruitment Team`;
}

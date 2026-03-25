TALASH — Full Project Roadmap
🧱 Phase 0: Setup (Day 1–2)
Tech Stack to decide on (recommended):

Backend: Python + FastAPI
LLM: Claude API (via Anthropic SDK) — fits perfectly since this is a CS417 LLMs course
PDF Parsing: PyMuPDF or pdfplumber
Frontend: React + Tailwind + Recharts (for dashboards)
Database: SQLite or PostgreSQL for structured candidate data
Storage: Local folder-based CV ingestion (as required)


🏁 Milestone 1 — Proposal, Architecture, Prototype (Week 1–3)
Step 1: System Architecture Design
Draw a clear data flow diagram showing: CV Upload → Parser → Structured Data → LLM Analysis Modules → Database → Frontend Dashboard. This is worth 4 marks so make it detailed.
Step 2: UI/UX Wireframes
Sketch screens for: CV upload page, candidate list view, individual candidate analysis page, graphical dashboard, and the email draft view. Use Figma or even pen and paper scanned in.
Step 3: Build the Preprocessing Module (this is the big deliverable for M1 — 12 marks)
This is your most important task for milestone 1. The steps are:

Accept a folder of PDF CVs
Use pdfplumber to extract raw text from each PDF
Send that text to Claude API with a structured prompt asking it to return JSON with fields: personal info, education, experience, skills, publications, patents, books
Save that JSON into your database and also export to CSV/Excel

Step 4: Early Prototype
Show upload working + extraction output from 1–2 real CVs. Even a basic CLI demo counts.

⚙️ Milestone 2 — Core Analysis Pipeline (Week 4–7)
Once parsing works, you build the analysis modules one by one. Do them in this order of priority:
Step 5: Educational Profile Analysis
Prompt Claude to analyze the extracted education data for: SSC/HSSC scores, UG/PG CGPA, degree sequence, institutional quality (use THE/QS ranking sites), educational gaps, and gap justification via work experience. Output a structured summary.
Step 6: Professional Experience Analysis
Prompt Claude to check timeline consistency — overlapping jobs, overlapping jobs with education, unexplained gaps, and career progression logic.
Step 7: Missing Information Detection + Email Drafting
After analysis, identify what fields are empty or unclear. Prompt Claude to write a personalized email to that specific candidate requesting the missing info.
Step 8: Connect outputs to the web app
By end of M2 you need: a working web UI, tabular candidate output, and at least basic charts.

🚀 Milestone 3 — Full System (Week 8–12)
Step 9: Research Profile Analysis
This is the most complex module (7 marks for journals/conferences alone). For each publication:

Extract journal name + ISSN → verify WoS/Scopus indexing via web search or API
Determine quartile ranking (Q1–Q4)
Identify authorship role (first/corresponding/co-author)
For conferences, check CORE portal for A* ranking

Step 10: Topic Variability + Co-author Analysis
Feed all publication titles/abstracts into Claude and ask it to cluster them by theme, compute a diversity score, and identify the dominant research area. For co-authors, extract all author lists and find recurring names.
Step 11: Supervision, Patents, Books
These are simpler — extract structured data from the CV and verify with online links where provided.
Step 12: Skill Alignment Module
Compare skills listed in CV against job descriptions, publication themes, and work history. Classify each skill as strongly/partially/weakly evidenced.
Step 13: Candidate Summary + Ranking Dashboard
Prompt Claude to generate a final paragraph summary per candidate. Build a comparison dashboard showing all candidates side by side. The extra credit ranking module (if you have time) scores each candidate numerically across all dimensions.

💡 Key Tips

Start prompts early. Most of your grade depends on how well you prompt Claude to analyze CVs — spend real time on prompt engineering.
Use structured JSON outputs from Claude throughout (tell Claude to respond only in JSON). It'll make connecting to your frontend much easier.
Keep GitHub updated weekly — the rubric explicitly penalizes last-minute bulk uploads.
Use real CVs from the dataset link to test each module as you build it, not at the end.
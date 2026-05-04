export default function OverviewPage() {
  return (
    <section className="page-grid">
      <article className="panel hero-panel reveal">
        <p className="eyebrow">PROJECT SUMMARY</p>
        <h2>About TALASH</h2>
        <p className="muted">
          TALASH is a candidate intelligence platform for recruiting and profile analysis.
          It brings together CV ingestion, profile parsing, research signals, missing-information
          detection, and reporting into one workflow so candidate records can be reviewed and
          organized more efficiently.
        </p>
        <p className="muted">
          The application is designed to support structured document intake, automated
          extraction, and clear downstream review for educational history, work experience,
          publications, and follow-up actions.
        </p>
      </article>
    </section>
  );
}
export default function GradeReport({ result, onClose }) {
  if (!result) return null;

  const {
    branch,
    classId,
    criteria = [],
    overallVerdict,
    revisionPriority,
    summary,
    verdictCounts,
    gradedAt,
  } = result;

  return (
    <div className="grade-report-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="grade-report" role="dialog" aria-label={`Grade report for ${branch}`}>
        <div className="grade-report__header">
          <div>
            <h2 className="grade-report__title">{branch}</h2>
            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
              {classId} • Graded {gradedAt ? new Date(gradedAt).toLocaleString() : 'now'}
            </span>
          </div>
          <button className="grade-report__close" onClick={onClose} aria-label="Close report">
            ✕
          </button>
        </div>

        {/* Overall Verdict */}
        <div style={{ marginBottom: 'var(--space-xl)' }}>
          <span
            className={`grade-card__verdict grade-card__verdict--${
              overallVerdict === 'ready_to_move_on' ? 'ready' : 'revision'
            }`}
            style={{ fontSize: '0.85rem', padding: '6px 14px' }}
          >
            {overallVerdict === 'ready_to_move_on' ? '✅ Ready to Move On' : '🔄 Needs Revision'}
          </span>
        </div>

        {/* Summary */}
        {summary && (
          <div className="grade-report__summary">
            {summary}
          </div>
        )}

        {/* Revision Priority */}
        {revisionPriority && overallVerdict === 'needs_revision' && (
          <div className="grade-report__revision">
            <strong>🎯 Priority Fix:</strong>
            {revisionPriority}
          </div>
        )}

        {/* Criteria Table */}
        {criteria.length > 0 && (
          <>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: 'var(--space-xl) 0 var(--space-md)' }}>
              Per-Criterion Breakdown
            </h3>
            <table className="criteria-table">
              <tbody>
                {criteria.map((c, i) => (
                  <tr key={i} className="criteria-row">
                    <td>{c.number || i + 1}</td>
                    <td>
                      <div className="criteria-row__name">{c.criterion}</div>
                      <span className={`criteria-row__verdict-chip criteria-row__verdict-chip--${c.verdict}`}>
                        {c.verdict === 'met' ? '✓ Met' : c.verdict === 'partial' ? '◐ Partial' : '✗ Not Met'}
                      </span>

                      {c.evidence && (
                        <div className="criteria-row__evidence">
                          {c.evidence}
                        </div>
                      )}

                      {c.reasoning && (
                        <div className="criteria-row__reasoning">
                          {c.reasoning}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {/* Verdict Counts Summary */}
        {verdictCounts && (
          <div className="grade-summary-bar" style={{ marginTop: 'var(--space-xl)' }}>
            <div className="grade-summary-stat">
              <span className="grade-summary-stat__value" style={{ color: 'var(--color-met)' }}>
                {verdictCounts.met}
              </span>
              <span className="grade-summary-stat__label">Met</span>
            </div>
            <div className="grade-summary-stat">
              <span className="grade-summary-stat__value" style={{ color: 'var(--color-partial)' }}>
                {verdictCounts.partial}
              </span>
              <span className="grade-summary-stat__label">Partial</span>
            </div>
            <div className="grade-summary-stat">
              <span className="grade-summary-stat__value" style={{ color: 'var(--color-not-met)' }}>
                {verdictCounts.not_met}
              </span>
              <span className="grade-summary-stat__label">Not Met</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

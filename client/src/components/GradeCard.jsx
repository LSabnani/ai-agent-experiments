export default function GradeCard({ result, onClick }) {
  const { branch, overallVerdict, verdictCounts, summary, noSubmission, error } = result;

  const totalCriteria = (verdictCounts?.met || 0) + (verdictCounts?.partial || 0) + (verdictCounts?.not_met || 0);

  const getVerdictClass = () => {
    if (error || noSubmission) return 'error';
    return overallVerdict === 'ready_to_move_on' ? 'ready' : 'revision';
  };

  const getVerdictLabel = () => {
    if (noSubmission) return 'No Submission';
    if (error) return 'Error';
    return overallVerdict === 'ready_to_move_on' ? 'Ready to Move On' : 'Needs Revision';
  };

  const verdictType = getVerdictClass();

  // Calculate bar segment widths
  const metWidth = totalCriteria > 0 ? (verdictCounts.met / totalCriteria) * 100 : 0;
  const partialWidth = totalCriteria > 0 ? (verdictCounts.partial / totalCriteria) * 100 : 0;
  const notMetWidth = totalCriteria > 0 ? (verdictCounts.not_met / totalCriteria) * 100 : 0;

  return (
    <div className="glass-card grade-card" onClick={onClick} role="button" tabIndex={0}>
      <div className={`grade-card__status-bar grade-card__status-bar--${verdictType}`} />

      <div className="grade-card__header">
        <span className="grade-card__student">{branch}</span>
        <span className={`grade-card__verdict grade-card__verdict--${verdictType}`}>
          {getVerdictLabel()}
        </span>
      </div>

      {totalCriteria > 0 && (
        <>
          <div className="grade-card__criteria-bar">
            {metWidth > 0 && (
              <div
                className="grade-card__criteria-segment grade-card__criteria-segment--met"
                style={{ width: `${metWidth}%` }}
              />
            )}
            {partialWidth > 0 && (
              <div
                className="grade-card__criteria-segment grade-card__criteria-segment--partial"
                style={{ width: `${partialWidth}%` }}
              />
            )}
            {notMetWidth > 0 && (
              <div
                className="grade-card__criteria-segment grade-card__criteria-segment--not-met"
                style={{ width: `${notMetWidth}%` }}
              />
            )}
          </div>

          <div className="grade-card__counts">
            <span className="grade-card__count">
              <span className="grade-card__count-dot grade-card__count-dot--met" />
              {verdictCounts.met} met
            </span>
            <span className="grade-card__count">
              <span className="grade-card__count-dot grade-card__count-dot--partial" />
              {verdictCounts.partial} partial
            </span>
            <span className="grade-card__count">
              <span className="grade-card__count-dot grade-card__count-dot--not-met" />
              {verdictCounts.not_met} not met
            </span>
          </div>
        </>
      )}

      <div className="grade-card__expand">Click to view full report →</div>
    </div>
  );
}

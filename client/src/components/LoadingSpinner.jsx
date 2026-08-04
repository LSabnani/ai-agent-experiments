export default function LoadingSpinner({ text, subtext, progress, total }) {
  const hasProgress = progress !== undefined && total !== undefined;
  const progressPercent = hasProgress ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="loading-container">
      <div className="spinner" />
      <div className="loading-container__text">{text || 'Processing…'}</div>
      {subtext && <div className="loading-container__subtext">{subtext}</div>}
      {hasProgress && (
        <>
          <div className="progress-bar">
            <div
              className="progress-bar__fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="loading-container__subtext" style={{ marginTop: '0.5rem' }}>
            {progress} of {total} ({progressPercent}%)
          </div>
        </>
      )}
    </div>
  );
}

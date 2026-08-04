export default function BranchList({
  branches,
  selectedBranches,
  onToggleBranch,
  onSelectAll,
  onDeselectAll,
  onGrade,
  loading,
}) {
  const selectedCount = selectedBranches.length;

  return (
    <section className="branch-list">
      <h2>Select Students to Grade</h2>
      <p>Each branch represents a student's fork. Select which students to grade.</p>

      <div className="branch-list__controls">
        <div className="branch-list__actions">
          <button className="btn btn-ghost" onClick={onSelectAll}>
            Select All ({branches.length})
          </button>
          <button className="btn btn-ghost" onClick={onDeselectAll}>
            Deselect All
          </button>
        </div>

        <button
          id="grade-selected-btn"
          className="btn btn-primary"
          disabled={selectedCount === 0 || loading}
          onClick={onGrade}
        >
          {loading ? (
            <>
              <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2, marginBottom: 0 }} />
              Grading…
            </>
          ) : (
            `🎓 Grade Selected (${selectedCount})`
          )}
        </button>
      </div>

      {branches.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">🌿</div>
          <div className="empty-state__text">
            No student branches found. Make sure students have pushed their work to separate branches.
          </div>
        </div>
      ) : (
        <div className="branch-grid stagger-enter">
          {branches.map((branch) => {
            const isSelected = selectedBranches.includes(branch.name);
            return (
              <div
                key={branch.name}
                className={`glass-card branch-card ${isSelected ? 'branch-card--selected' : ''}`}
                onClick={() => onToggleBranch(branch.name)}
                role="checkbox"
                aria-checked={isSelected}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onToggleBranch(branch.name)}
              >
                <div className="branch-card__checkbox">
                  <span className="branch-card__checkbox-icon">✓</span>
                </div>
                <span className="branch-card__name">{branch.name}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

import { useState, useCallback } from 'react';
import Header from './components/Header.jsx';
import RepoInput from './components/RepoInput.jsx';
import ClassSelector from './components/ClassSelector.jsx';
import CriteriaViewer from './components/CriteriaViewer.jsx';
import BranchList from './components/BranchList.jsx';
import GradeCard from './components/GradeCard.jsx';
import GradeReport from './components/GradeReport.jsx';
import LoadingSpinner from './components/LoadingSpinner.jsx';
import * as api from './utils/api.js';

export default function App() {
  // Navigation
  const [step, setStep] = useState(1);

  // Step 1: Repo
  const [cloning, setCloning] = useState(false);
  const [classes, setClasses] = useState([]);
  const [branches, setBranches] = useState([]);
  const [error, setError] = useState(null);

  // Step 2: Class selection
  const [selectedClass, setSelectedClass] = useState(null);
  const [criteria, setCriteria] = useState(null);
  const [loadingCriteria, setLoadingCriteria] = useState(false);

  // Step 3: Branch selection
  const [selectedBranches, setSelectedBranches] = useState([]);

  // Step 4: Grading results
  const [grading, setGrading] = useState(false);
  const [gradingProgress, setGradingProgress] = useState({ current: 0, total: 0 });
  const [results, setResults] = useState([]);
  const [expandedResult, setExpandedResult] = useState(null);

  // --- Step 1: Clone Repo ---
  const handleClone = useCallback(async (url) => {
    setCloning(true);
    setError(null);
    try {
      const data = await api.cloneRepo(url);
      setClasses(data.classes || []);
      setBranches(data.branches || []);
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setCloning(false);
    }
  }, []);

  // --- Step 2: Select Class ---
  const handleSelectClass = useCallback(async (cls) => {
    setSelectedClass(cls);
    setLoadingCriteria(true);
    setError(null);
    try {
      const data = await api.getClassCriteria(cls.id);
      setCriteria(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCriteria(false);
    }
  }, []);

  const handleProceedToBranches = useCallback(() => {
    setStep(3);
  }, []);

  // --- Step 3: Branch Selection ---
  const toggleBranch = useCallback((name) => {
    setSelectedBranches((prev) =>
      prev.includes(name) ? prev.filter((b) => b !== name) : [...prev, name]
    );
  }, []);

  const selectAllBranches = useCallback(() => {
    setSelectedBranches(branches.map((b) => b.name));
  }, [branches]);

  const deselectAllBranches = useCallback(() => {
    setSelectedBranches([]);
  }, []);

  // --- Step 4: Grade ---
  const handleGrade = useCallback(async () => {
    setGrading(true);
    setError(null);
    setResults([]);
    setStep(4);
    setGradingProgress({ current: 0, total: selectedBranches.length });

    try {
      // Grade students one at a time so we can show progress
      const allResults = [];
      for (let i = 0; i < selectedBranches.length; i++) {
        setGradingProgress({ current: i, total: selectedBranches.length, currentStudent: selectedBranches[i] });
        try {
          const data = await api.gradeStudent(selectedBranches[i], selectedClass.id);
          allResults.push(data.result);
          setResults([...allResults]);
        } catch (err) {
          allResults.push({
            branch: selectedBranches[i],
            classId: selectedClass.id,
            criteria: [],
            overallVerdict: 'needs_revision',
            revisionPriority: `Grading error: ${err.message}`,
            summary: `Failed to grade: ${err.message}`,
            verdictCounts: { met: 0, partial: 0, not_met: 0 },
            error: true,
          });
          setResults([...allResults]);
        }
      }
      setGradingProgress({ current: selectedBranches.length, total: selectedBranches.length });
    } catch (err) {
      setError(err.message);
    } finally {
      setGrading(false);
    }
  }, [selectedBranches, selectedClass]);

  // --- Navigation helpers ---
  const goBack = useCallback(() => {
    if (step > 1) {
      if (step === 4) {
        setResults([]);
        setExpandedResult(null);
      }
      setStep(step - 1);
    }
  }, [step]);

  // --- Compute dashboard stats ---
  const totalGraded = results.length;
  const readyCount = results.filter((r) => r.overallVerdict === 'ready_to_move_on').length;
  const revisionCount = results.filter(
    (r) => r.overallVerdict === 'needs_revision' && !r.noSubmission && !r.error
  ).length;
  const noSubmissionCount = results.filter((r) => r.noSubmission).length;

  return (
    <div className="app-container">
      <Header currentStep={step} />

      {error && <div className="error-message">⚠️ {error}</div>}

      {/* Step 1: Connect Repo */}
      {step === 1 && (
        <RepoInput onClone={handleClone} loading={cloning} />
      )}

      {/* Step 2: Select Class */}
      {step === 2 && (
        <>
          <div className="nav-row">
            <button className="btn btn-ghost" onClick={goBack}>
              ← Back
            </button>
            {selectedClass && criteria && (
              <button className="btn btn-primary" onClick={handleProceedToBranches}>
                Continue with {selectedClass.id} →
              </button>
            )}
          </div>

          <ClassSelector
            classes={classes}
            selectedClass={selectedClass}
            onSelectClass={handleSelectClass}
          />

          {loadingCriteria && <LoadingSpinner text="Loading criteria…" />}

          {criteria && selectedClass && !loadingCriteria && (
            <CriteriaViewer
              homework={criteria.homework}
              gradingCriteria={criteria.gradingCriteria}
            />
          )}
        </>
      )}

      {/* Step 3: Select Students */}
      {step === 3 && (
        <>
          <div className="nav-row">
            <button className="btn btn-ghost" onClick={goBack}>
              ← Back to Class Selection
            </button>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Grading: <strong style={{ color: 'var(--accent-cyan)' }}>{selectedClass?.id}</strong>
            </span>
          </div>

          <BranchList
            branches={branches}
            selectedBranches={selectedBranches}
            onToggleBranch={toggleBranch}
            onSelectAll={selectAllBranches}
            onDeselectAll={deselectAllBranches}
            onGrade={handleGrade}
            loading={grading}
          />
        </>
      )}

      {/* Step 4: Results Dashboard */}
      {step === 4 && (
        <section className="grade-dashboard">
          <div className="nav-row">
            <button className="btn btn-ghost" onClick={goBack}>
              ← Back to Student Selection
            </button>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {selectedClass?.id} — {selectedClass?.topic}
            </span>
          </div>

          <h2>Grading Results</h2>
          <p>
            {grading
              ? `Grading in progress…`
              : `${totalGraded} student${totalGraded !== 1 ? 's' : ''} graded for ${selectedClass?.id}`}
          </p>

          {grading && (
            <LoadingSpinner
              text={`Grading ${gradingProgress.currentStudent || '…'}`}
              subtext="Claude is reviewing the submission against the rubric"
              progress={gradingProgress.current}
              total={gradingProgress.total}
            />
          )}

          {results.length > 0 && (
            <>
              {/* Summary stats */}
              <div className="grade-summary-bar">
                <div className="grade-summary-stat">
                  <span className="grade-summary-stat__value">{totalGraded}</span>
                  <span className="grade-summary-stat__label">Total</span>
                </div>
                <div className="grade-summary-stat">
                  <span className="grade-summary-stat__value" style={{ color: 'var(--color-met)' }}>
                    {readyCount}
                  </span>
                  <span className="grade-summary-stat__label">Ready</span>
                </div>
                <div className="grade-summary-stat">
                  <span className="grade-summary-stat__value" style={{ color: 'var(--color-partial)' }}>
                    {revisionCount}
                  </span>
                  <span className="grade-summary-stat__label">Needs Revision</span>
                </div>
                {noSubmissionCount > 0 && (
                  <div className="grade-summary-stat">
                    <span className="grade-summary-stat__value" style={{ color: 'var(--color-not-met)' }}>
                      {noSubmissionCount}
                    </span>
                    <span className="grade-summary-stat__label">No Submission</span>
                  </div>
                )}
              </div>

              {/* Grade cards grid */}
              <div className="grade-cards-grid stagger-enter">
                {results.map((result) => (
                  <GradeCard
                    key={result.branch}
                    result={result}
                    onClick={() => setExpandedResult(result)}
                  />
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* Expanded Grade Report Modal */}
      {expandedResult && (
        <GradeReport result={expandedResult} onClose={() => setExpandedResult(null)} />
      )}
    </div>
  );
}

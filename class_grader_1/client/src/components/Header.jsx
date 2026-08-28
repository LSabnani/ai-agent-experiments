export default function Header({ currentStep }) {
  const steps = [
    { num: 1, label: 'Connect Repo' },
    { num: 2, label: 'Select Class' },
    { num: 3, label: 'Select Students' },
    { num: 4, label: 'View Grades' },
  ];

  return (
    <header className="header">
      <h1 className="header__title">Code Grader</h1>
      <p className="header__subtitle">
        AI-powered submission grading for Agent Engineering
      </p>

      <nav className="steps">
        {steps.map((step, i) => {
          let className = 'step';
          if (step.num === currentStep) className += ' step--active';
          else if (step.num < currentStep) className += ' step--completed';

          return (
            <div key={step.num}>
              {i > 0 && <span className="step-divider" style={{ marginRight: '0.5rem' }}>›</span>}
              <span className={className}>
                <span className="step__number">
                  {step.num < currentStep ? '✓' : step.num}
                </span>
                {step.label}
              </span>
            </div>
          );
        })}
      </nav>
    </header>
  );
}

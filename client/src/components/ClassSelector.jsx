export default function ClassSelector({ classes, selectedClass, onSelectClass }) {
  return (
    <section className="class-selector">
      <h2>Select a Class to Grade</h2>
      <p>Choose which assignment to grade. Each class has its own rubric and golden solution.</p>

      <div className="class-grid stagger-enter">
        {classes.map((cls) => {
          const isSelected = selectedClass?.id === cls.id;
          let cardClass = 'glass-card class-card';
          if (isSelected) cardClass += ' class-card--selected';
          if (!cls.ready) cardClass += ' class-card--disabled';

          return (
            <div
              key={cls.id}
              id={`class-card-${cls.id}`}
              className={cardClass}
              onClick={() => cls.ready && onSelectClass(cls)}
              role="button"
              tabIndex={cls.ready ? 0 : -1}
              onKeyDown={(e) => e.key === 'Enter' && cls.ready && onSelectClass(cls)}
            >
              <div className="class-card__number">Class {String(cls.number).padStart(2, '0')}</div>
              <div className="class-card__topic">{cls.topic}</div>
              <div className="class-card__badges">
                {cls.ready ? (
                  <span className="badge badge--ready">✓ Ready</span>
                ) : (
                  <>
                    {!cls.hasHomework && <span className="badge badge--missing">No homework.md</span>}
                    {!cls.hasGrading && <span className="badge badge--missing">No GRADING.md</span>}
                    {!cls.hasGoldenSolution && <span className="badge badge--missing">No golden solution</span>}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

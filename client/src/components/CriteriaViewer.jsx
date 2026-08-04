import { useState } from 'react';

export default function CriteriaViewer({ homework, gradingCriteria }) {
  const [activeTab, setActiveTab] = useState('grading');

  return (
    <div className="criteria-viewer">
      <div className="criteria-viewer__tabs">
        <button
          id="tab-grading"
          className={`criteria-viewer__tab ${activeTab === 'grading' ? 'criteria-viewer__tab--active' : ''}`}
          onClick={() => setActiveTab('grading')}
        >
          📋 GRADING.md
        </button>
        <button
          id="tab-homework"
          className={`criteria-viewer__tab ${activeTab === 'homework' ? 'criteria-viewer__tab--active' : ''}`}
          onClick={() => setActiveTab('homework')}
        >
          📝 homework.md
        </button>
      </div>

      <div className="criteria-viewer__content">
        {activeTab === 'grading' ? gradingCriteria : homework}
      </div>
    </div>
  );
}

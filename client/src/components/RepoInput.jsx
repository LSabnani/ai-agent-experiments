import { useState } from 'react';

export default function RepoInput({ onClone, loading }) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onClone(url.trim());
    }
  };

  const isValidUrl = url.match(/^https?:\/\/(www\.)?github\.com\/.+\/.+/);

  return (
    <section className="repo-input-section">
      <div className="glass-card glass-card--accent">
        <h2>Connect a GitHub Repository</h2>
        <p>
          Enter the URL of the course repository. The app will clone it and
          detect student branches and available class assignments.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <input
              id="repo-url-input"
              type="url"
              className="input-field"
              placeholder="https://github.com/org/agent_engineering"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
              autoFocus
            />
            <button
              id="clone-btn"
              type="submit"
              className="btn btn-primary"
              disabled={!isValidUrl || loading}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2, marginBottom: 0 }} />
                  Cloning…
                </>
              ) : (
                '🔗 Clone & Analyze'
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

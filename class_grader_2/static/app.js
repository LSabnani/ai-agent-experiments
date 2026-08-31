// ML Spec Grader Frontend Logic

function switchTab(tab) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

    if (tab === 'grade') {
        document.getElementById('tab-grade-btn').classList.add('active');
        document.getElementById('view-grade').classList.add('active');
    } else if (tab === 'instructor') {
        document.getElementById('tab-instructor-btn').classList.add('active');
        document.getElementById('view-instructor').classList.add('active');
        loadInstructorData();
    } else if (tab === 'traces') {
        document.getElementById('tab-traces-btn').classList.add('active');
        document.getElementById('view-traces').classList.add('active');
        loadTracesData();
    }
}

function setSample(name, folder, subfolder = '') {
    document.getElementById('student-name').value = name;
    document.getElementById('folder-path').value = folder;
    const subfolderEl = document.getElementById('subfolder-path');
    if (subfolderEl) {
        subfolderEl.value = subfolder;
    }
}

// Handle Form Submission for Grading
async function handleGradeSubmit(event) {
    event.preventDefault();

    const studentName = document.getElementById('student-name').value.trim();
    const folderPath = document.getElementById('folder-path').value.trim();
    const subfolderEl = document.getElementById('subfolder-path');
    const subfolder = subfolderEl ? subfolderEl.value.trim() : '';

    const statusBanner = document.getElementById('status-message');
    const submitBtn = document.getElementById('btn-submit-grade');
    const placeholder = document.getElementById('result-placeholder');
    const resultContent = document.getElementById('result-content');

    if (!studentName || !folderPath) return;

    // Set Loading State
    const isGit = folderPath.startsWith('http://') || folderPath.startsWith('https://') || folderPath.includes('github.com');
    statusBanner.className = 'status-banner loading';
    statusBanner.textContent = isGit 
        ? '⏳ Fetching repository from GitHub & evaluating with Gemini...' 
        : '⏳ Evaluating codebase with Gemini & logging telemetry traces...';
    statusBanner.classList.remove('hidden');
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/grade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_name: studentName,
                folder_name: folderPath,
                subfolder: subfolder || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Grading failed. Please check repository URL or folder path.');
        }

        // Render Result
        renderEvaluationResult(data);
        statusBanner.className = 'status-banner hidden';

    } catch (err) {
        statusBanner.className = 'status-banner error';
        statusBanner.textContent = `❌ ${err.message}`;
    } finally {
        submitBtn.disabled = false;
    }
}

function renderEvaluationResult(submission) {
    const placeholder = document.getElementById('result-placeholder');
    const resultContent = document.getElementById('result-content');
    const details = submission.evaluation_details;

    placeholder.classList.add('hidden');
    resultContent.classList.remove('hidden');

    document.getElementById('res-score').textContent = Math.round(submission.score);
    document.getElementById('res-grade').textContent = submission.letter_grade;
    document.getElementById('res-student-title').textContent = `${submission.student_name} Evaluation`;
    document.getElementById('res-summary').textContent = details ? details.summary : 'Evaluation complete.';
    document.getElementById('res-folder-tag').textContent = submission.folder_name;

    // Strengths
    const strengthsList = document.getElementById('res-strengths');
    strengthsList.innerHTML = '';
    if (details && details.strengths && details.strengths.length > 0) {
        details.strengths.forEach(s => {
            const li = document.createElement('li');
            li.textContent = s;
            strengthsList.appendChild(li);
        });
    } else {
        strengthsList.innerHTML = '<li>No significant strengths detected.</li>';
    }

    // Deductions
    const deductionsList = document.getElementById('res-deductions');
    deductionsList.innerHTML = '';
    if (details && details.deductions && details.deductions.length > 0) {
        details.deductions.forEach(d => {
            const li = document.createElement('li');
            li.textContent = d;
            deductionsList.appendChild(li);
        });
    } else {
        deductionsList.innerHTML = '<li>✓ Zero deductions! Perfect specification match.</li>';
    }

    // Detailed Criteria Breakdown with Deduction Reasons & Fix Recommendations
    const criteriaList = document.getElementById('res-criteria-list');
    criteriaList.innerHTML = '';
    if (details && details.criteria) {
        details.criteria.forEach(c => {
            const isPerfect = c.earned_score >= c.max_score;
            const badgeClass = c.status === 'PASS' ? 'badge-pass' : (c.status === 'PARTIAL' ? 'badge-partial' : 'badge-fail');
            
            let deductionHtml = '';
            if (!isPerfect && (c.deduction_reason || c.status !== 'PASS')) {
                const reasonText = c.deduction_reason || `Incomplete implementation: earned ${c.earned_score} out of ${c.max_score} pts.`;
                deductionHtml = `
                    <div style="margin-top: 10px; padding: 10px 14px; background: rgba(239, 68, 68, 0.12); border-left: 3px solid #ef4444; border-radius: 4px;">
                        <strong style="color: #f87171; font-size: 0.82rem; display: block; margin-bottom: 3px;">
                            ⚠️ Deduction Reason (-${(c.max_score - c.earned_score).toFixed(1)} pts):
                        </strong>
                        <span style="font-size: 0.85rem; color: #fecaca;">${escapeHtml(reasonText)}</span>
                    </div>
                `;
            }

            let fixHtml = '';
            if (!isPerfect && c.fix_recommendation) {
                fixHtml = `
                    <div style="margin-top: 8px; padding: 10px 14px; background: rgba(59, 130, 246, 0.12); border-left: 3px solid #3b82f6; border-radius: 4px;">
                        <strong style="color: #60a5fa; font-size: 0.82rem; display: block; margin-bottom: 3px;">
                            💡 How to Fix & Achieve Full Score:
                        </strong>
                        <span style="font-size: 0.85rem; color: #dbeafe;">${escapeHtml(c.fix_recommendation)}</span>
                    </div>
                `;
            }

            const card = document.createElement('div');
            card.className = 'criterion-card';
            card.innerHTML = `
                <div class="criterion-header">
                    <span class="criterion-title">${escapeHtml(c.title)}</span>
                    <div>
                        <span class="criterion-badge ${badgeClass}">${c.status}</span>
                        <span class="criterion-points" style="font-weight: 700;">${c.earned_score}/${c.max_score} pts</span>
                    </div>
                </div>
                <div class="criterion-feedback" style="margin-top: 6px; line-height: 1.5;">${escapeHtml(c.feedback)}</div>
                ${c.evidence ? `<div class="criterion-evidence" style="margin-top: 6px;"><strong>Evidence:</strong> ${escapeHtml(c.evidence)}</div>` : ''}
                ${deductionHtml}
                ${fixHtml}
            `;
            criteriaList.appendChild(card);
        });
    }
}

// Load Instructor Leaderboard & Student Summaries
async function loadInstructorData() {
    const tbody = document.getElementById('instructor-table-body');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Loading student records...</td></tr>';

    try {
        const response = await fetch('/api/instructor/students');
        const students = await response.json();

        // Update Statistics
        document.getElementById('stat-total-students').textContent = students.length;
        const totalSubs = students.reduce((acc, s) => acc + s.total_submissions, 0);
        document.getElementById('stat-total-subs').textContent = totalSubs;
        
        const topScore = students.length > 0 ? Math.max(...students.map(s => s.highest_score)) : 0;
        document.getElementById('stat-top-score').textContent = `${topScore.toFixed(1)}%`;

        if (students.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding: 30px;">No submissions recorded yet in outputs/scores.json.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        students.forEach(s => {
            const row = document.createElement('tr');
            const formattedTime = new Date(s.latest_submission_time).toLocaleString();
            
            row.innerHTML = `
                <td>
                    <a href="javascript:void(0)" class="student-link" onclick="openStudentModal('${escapeHtml(s.student_name)}')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                        <strong>${escapeHtml(s.student_name)}</strong>
                    </a>
                </td>
                <td>
                    <span class="criterion-badge badge-pass" style="font-size: 0.85rem;">
                        ${s.highest_score.toFixed(1)}% (${s.highest_grade})
                    </span>
                </td>
                <td>
                    <span class="criterion-badge ${s.latest_score >= 80 ? 'badge-pass' : (s.latest_score >= 60 ? 'badge-partial' : 'badge-fail')}">
                        ${s.latest_score.toFixed(1)}% (${s.latest_grade})
                    </span>
                </td>
                <td><small style="color: var(--text-muted);">${formattedTime}</small></td>
                <td><span style="font-weight: 700;">${s.total_submissions}</span></td>
                <td>
                    <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="openStudentModal('${escapeHtml(s.student_name)}')">
                        View Submissions
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--danger);">Failed to load instructor data: ${err.message}</td></tr>`;
    }
}

// Load Gemini Telemetry Traces
async function loadTracesData() {
    const listEl = document.getElementById('traces-list');
    listEl.innerHTML = '<div class="text-center" style="padding: 20px;">Fetching telemetry traces from outputs/gemini_traces.jsonl...</div>';

    try {
        const response = await fetch('/api/traces?limit=40');
        const data = await response.json();
        const traces = data.traces || [];

        if (traces.length === 0) {
            listEl.innerHTML = '<div class="text-center" style="padding: 30px; color: var(--text-muted);">No telemetry traces recorded yet. Run a grading evaluation to generate traces.</div>';
            return;
        }

        listEl.innerHTML = '';
        traces.reverse().forEach(t => {
            const timeStr = new Date(t.timestamp).toLocaleTimeString();
            const evType = t.event_type || 'EVENT';
            const dur = t.duration_ms ? `${t.duration_ms.toFixed(1)}ms` : '';
            
            let badgeClass = 'badge-pass';
            if (evType === 'MODEL_CALL') badgeClass = 'badge-partial';
            if (evType === 'MODEL_RESPONSE') badgeClass = 'badge-pass';
            if (evType === 'TOOL_INVOCATION') badgeClass = 'badge-partial';
            if (evType === 'TOOL_RESPONSE') badgeClass = 'badge-pass';
            if (evType === 'SKILL_USAGE') badgeClass = 'badge-pass';

            const item = document.createElement('div');
            item.className = 'history-item';
            item.innerHTML = `
                <div class="history-header">
                    <div>
                        <span class="criterion-badge ${badgeClass}" style="font-size: 0.8rem; font-weight: 700;">${evType}</span>
                        ${dur ? `<span style="margin-left: 8px; font-size: 0.8rem; color: var(--primary); font-weight: 600;">⚡ ${dur}</span>` : ''}
                    </div>
                    <span style="font-size: 0.78rem; color: var(--text-muted);">${timeStr}</span>
                </div>
                <pre style="background: rgba(0,0,0,0.35); padding: 10px; border-radius: 6px; font-size: 0.78rem; font-family: 'JetBrains Mono', monospace; overflow-x: auto; color: #cbd5e1; margin-top: 8px;">${escapeHtml(JSON.stringify(t.details, null, 2))}</pre>
            `;
            listEl.appendChild(item);
        });

    } catch (err) {
        listEl.innerHTML = `<div class="text-center" style="color: var(--danger); padding: 20px;">Error loading traces: ${err.message}</div>`;
    }
}

// Open Drill-Down Modal Showing All Submissions for a Student
async function openStudentModal(studentName) {
    const modal = document.getElementById('student-modal');
    const nameEl = document.getElementById('modal-student-name');
    const listEl = document.getElementById('modal-submissions-list');

    nameEl.textContent = `${studentName}'s Submissions`;
    listEl.innerHTML = '<div style="text-align: center; padding: 20px;">Loading submission history...</div>';
    modal.classList.remove('hidden');

    try {
        const response = await fetch(`/api/instructor/students/${encodeURIComponent(studentName)}/submissions`);
        const submissions = await response.json();

        if (!submissions || submissions.length === 0) {
            listEl.innerHTML = '<div style="text-align: center; padding: 20px;">No submissions found for this student.</div>';
            return;
        }

        listEl.innerHTML = '';
        submissions.forEach((sub, idx) => {
            const timeStr = new Date(sub.timestamp).toLocaleString();
            const details = sub.evaluation_details;
            const item = document.createElement('div');
            item.className = 'history-item';
            
            let criteriaHtml = '';
            if (details && details.criteria) {
                criteriaHtml = `
                    <div style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
                        ${details.criteria.map(c => {
                            const isPerf = c.earned_score >= c.max_score;
                            return `
                                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                        <strong style="font-size: 0.82rem;">${escapeHtml(c.title)}</strong>
                                        <span class="criterion-badge ${c.status === 'PASS' ? 'badge-pass' : (c.status === 'PARTIAL' ? 'badge-partial' : 'badge-fail')}" style="font-size: 0.72rem;">
                                            ${c.earned_score}/${c.max_score} pts (${c.status})
                                        </span>
                                    </div>
                                    <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(c.feedback)}</div>
                                    ${!isPerf && c.deduction_reason ? `<div style="font-size: 0.76rem; color: #f87171; margin-top: 4px;">⚠️ <strong>Deduction:</strong> ${escapeHtml(c.deduction_reason)}</div>` : ''}
                                    ${!isPerf && c.fix_recommendation ? `<div style="font-size: 0.76rem; color: #60a5fa; margin-top: 2px;">💡 <strong>Fix:</strong> ${escapeHtml(c.fix_recommendation)}</div>` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            }

            item.innerHTML = `
                <div class="history-header">
                    <div>
                        <span class="history-score" style="color: ${sub.score >= 80 ? 'var(--success)' : (sub.score >= 60 ? 'var(--warning)' : 'var(--danger)')};">
                            ${sub.score.toFixed(1)}% (${sub.letter_grade})
                        </span>
                        <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 8px;">Submission #${submissions.length - idx}</span>
                    </div>
                    <span style="font-size: 0.8rem; color: var(--text-muted);">${timeStr}</span>
                </div>
                <div class="history-folder">Folder: ${escapeHtml(sub.folder_name)}</div>
                ${details ? `<div class="history-summary">${escapeHtml(details.summary)}</div>` : ''}
                ${criteriaHtml}
            `;
            listEl.appendChild(item);
        });

    } catch (err) {
        listEl.innerHTML = `<div style="color: var(--danger); text-align: center;">Error loading history: ${err.message}</div>`;
    }
}

function closeStudentModal() {
    document.getElementById('student-modal').classList.add('hidden');
}

// Close modal on escape key or clicking backdrop
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeStudentModal();
});
document.getElementById('student-modal').addEventListener('click', (e) => {
    if (e.target.id === 'student-modal') closeStudentModal();
});

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
}

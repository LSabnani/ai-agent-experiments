// ML Spec Grader Frontend Logic

let currentSubmission = null;
let submissionsConfigData = { classes: [], config: {} };

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSubmissionsConfig();
});

// Load SUBMISSIONS.yaml Config and populate Class & Assignment dropdowns
async function loadSubmissionsConfig() {
    try {
        const resp = await fetch('/api/config/submissions');
        if (!resp.ok) return;
        submissionsConfigData = await resp.json();
        
        const classSelect = document.getElementById('class-select');
        if (!classSelect) return;

        classSelect.innerHTML = '<option value="">-- Select Class --</option>';
        (submissionsConfigData.classes || []).forEach(cls => {
            const opt = document.createElement('option');
            opt.value = cls;
            opt.textContent = cls;
            classSelect.appendChild(opt);
        });

        // If there is only one class, auto-select it
        if (submissionsConfigData.classes && submissionsConfigData.classes.length === 1) {
            classSelect.value = submissionsConfigData.classes[0];
            handleClassChange();
        }
    } catch (e) {
        console.error('Failed to load submissions config:', e);
    }
}

function handleClassChange() {
    const classSelect = document.getElementById('class-select');
    const assignmentSelect = document.getElementById('assignment-select');
    const selectedClass = classSelect.value;

    assignmentSelect.innerHTML = '<option value="">-- Select Assignment --</option>';

    if (!selectedClass || !submissionsConfigData.config[selectedClass]) {
        document.getElementById('assignment-criteria-info').classList.add('hidden');
        return;
    }

    const assignments = Object.keys(submissionsConfigData.config[selectedClass]);
    assignments.forEach(assign => {
        const opt = document.createElement('option');
        opt.value = assign;
        opt.textContent = assign;
        assignmentSelect.appendChild(opt);
    });

    // Auto-select first assignment if available
    if (assignments.length > 0) {
        assignmentSelect.value = assignments[0];
        handleAssignmentChange();
    } else {
        document.getElementById('assignment-criteria-info').classList.add('hidden');
    }
}

function handleAssignmentChange() {
    const classSelect = document.getElementById('class-select');
    const assignmentSelect = document.getElementById('assignment-select');
    const banner = document.getElementById('assignment-criteria-info');
    const list = document.getElementById('assignment-criteria-list');

    const selectedClass = classSelect.value;
    const selectedAssign = assignmentSelect.value;

    if (!selectedClass || !selectedAssign || !submissionsConfigData.config[selectedClass]) {
        banner.classList.add('hidden');
        return;
    }

    const criteria = submissionsConfigData.config[selectedClass][selectedAssign] || [];
    if (criteria.length === 0) {
        banner.classList.add('hidden');
        return;
    }

    list.innerHTML = '';
    criteria.forEach(c => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${escapeHtml(c.criterion)}</strong>: <span style="color: #f87171; font-weight: 700;">-${c.weight_percent}% penalty</span> if missing`;
        list.appendChild(li);
    });
    banner.classList.remove('hidden');
}

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

function setSample(name, folder) {
    document.getElementById('student-name').value = name;
    document.getElementById('folder-path').value = folder;
}

// Handle Form Submission for Grading
async function handleGradeSubmit(event) {
    event.preventDefault();

    const studentName = document.getElementById('student-name').value.trim();
    const folderPath = document.getElementById('folder-path').value.trim();

    const classSelect = document.getElementById('class-select');
    const assignmentSelect = document.getElementById('assignment-select');
    const className = classSelect ? classSelect.value : '';
    const assignmentName = assignmentSelect ? assignmentSelect.value : '';

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
        : '⏳ Reading local folder & evaluating codebase with Gemini...';
    statusBanner.classList.remove('hidden');
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/grade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_name: studentName,
                folder_name: folderPath,
                subfolder: null,
                class_name: className || null,
                assignment_name: assignmentName || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'The grader is not available at this time. Please check repository URL or folder path.');
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
    currentSubmission = submission;
    const placeholder = document.getElementById('result-placeholder');
    const resultContent = document.getElementById('result-content');
    const details = submission.evaluation_details;

    placeholder.classList.add('hidden');
    resultContent.classList.remove('hidden');

    document.getElementById('res-score').textContent = Math.round(submission.score);
    document.getElementById('res-grade').textContent = submission.letter_grade;
    document.getElementById('res-student-title').textContent = `${submission.student_name} Evaluation`;
    
    // Summary
    document.getElementById('res-summary').innerHTML = escapeHtml(details ? details.summary : 'Evaluation complete.').replace(/\n/g, '<br>');
    document.getElementById('res-folder-tag').textContent = submission.folder_name;

    // Model Used Tag
    const modelName = submission.model_used || (details && details.model_used) || 'Gemini AI';
    const modelTag = document.getElementById('res-model-tag');
    if (modelTag) {
        modelTag.textContent = `🤖 Model: ${modelName}`;
    }

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

    // Detailed Criteria Breakdown with Mandatory criteria at the top
    const criteriaList = document.getElementById('res-criteria-list');
    criteriaList.innerHTML = '';
    if (details && details.criteria) {
        details.criteria.forEach((c, idx) => {
            const isPerfect = c.earned_score >= c.max_score;
            const isMandatory = c.is_mandatory || c.category === 'Mandatory Requirement' || (c.id && c.id.startsWith('mand_'));
            
            let badgeClass = c.status === 'PASS' ? 'badge-pass' : (c.status === 'PARTIAL' ? 'badge-partial' : 'badge-fail');
            
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
            if (isMandatory) {
                card.style.border = isPerfect ? '1px solid rgba(16, 185, 129, 0.4)' : '2px solid rgba(239, 68, 68, 0.6)';
                card.style.background = isPerfect ? 'rgba(16, 185, 129, 0.04)' : 'rgba(239, 68, 68, 0.06)';
            }

            card.innerHTML = `
                <div class="criterion-header">
                    <div>
                        ${isMandatory ? '<span class="criterion-badge" style="background: rgba(239, 68, 68, 0.2); color: #fca5a5; font-size: 0.72rem; margin-right: 6px; border: 1px solid rgba(239, 68, 68, 0.4);">⭐ MANDATORY REQUIREMENT</span>' : ''}
                        <span class="criterion-title">${escapeHtml(c.title)}</span>
                    </div>
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

function viewCurrentReport() {
    if (!currentSubmission || !currentSubmission.id) {
        alert('Please run a grading evaluation first to view the report.');
        return;
    }
    const endpoint = `/api/submissions/${currentSubmission.id}/report`;
    window.open(endpoint, '_blank');
}

function downloadCurrentReport(format) {
    if (!currentSubmission || !currentSubmission.id) {
        alert('Please run a grading evaluation first to download the report.');
        return;
    }
    
    // Direct native browser download
    const endpoint = `/api/submissions/${currentSubmission.id}/download/${format}`;
    const safeName = (currentSubmission.student_name || 'student').replace(/[^a-zA-Z0-9_-]/g, '_');
    const a = document.createElement('a');
    a.href = endpoint;
    a.download = `${safeName}_grade_report.${format}`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        if (a.parentNode) document.body.removeChild(a);
    }, 500);
}

// State for Instructor View Filtering & Sorting
let instructorStudentsData = [];
let instructorSelectedStudent = '';
let instructorSelectedClass = '';
let instructorSelectedAssignment = '';
let currentInstructorSort = { column: 'highest_score', order: 'desc' };

// Load Instructor Leaderboard & Student Summaries
async function loadInstructorData() {
    const tbody = document.getElementById('instructor-table-body');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">Loading student records...</td></tr>';
    }

    try {
        const response = await fetch('/api/instructor/students');
        instructorStudentsData = await response.json();

        // Populate Dropdowns (Single Selects)
        populateStudentDropdown(instructorStudentsData);
        populateInstructorClassAndAssignmentFilters(instructorStudentsData);

        // Render Table with active filters & sorting
        renderInstructorTable();

    } catch (err) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center" style="color: var(--danger);">Failed to load instructor data: ${escapeHtml(err.message)}</td></tr>`;
        }
    }
}

// Populate Student Names Dropdown (Single Select)
function populateStudentDropdown(students) {
    const studentSelect = document.getElementById('instructor-student-filter');
    if (!studentSelect) return;

    const uniqueStudents = Array.from(new Set(students.map(s => s.student_name.trim()))).sort();
    const currentVal = studentSelect.value || instructorSelectedStudent;

    studentSelect.innerHTML = '<option value="">All Students</option>';
    uniqueStudents.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        if (name === currentVal) opt.selected = true;
        studentSelect.appendChild(opt);
    });

    instructorSelectedStudent = studentSelect.value;
}

// Handle Student Filter Change
function handleInstructorStudentFilterChange() {
    const studentSelect = document.getElementById('instructor-student-filter');
    instructorSelectedStudent = studentSelect ? studentSelect.value : '';
    renderInstructorTable();
}

// Populate Course & Assignment Filter Options
function populateInstructorClassAndAssignmentFilters(students) {
    const classSelect = document.getElementById('instructor-class-filter');
    if (!classSelect) return;

    // Collect all unique classes from config and student records
    const classSet = new Set();
    if (submissionsConfigData && submissionsConfigData.classes) {
        submissionsConfigData.classes.forEach(c => classSet.add(c));
    }
    students.forEach(s => {
        if (s.latest_class && s.latest_class !== '--') classSet.add(s.latest_class);
    });

    const currentClass = classSelect.value || instructorSelectedClass;
    classSelect.innerHTML = '<option value="">All Courses / Classes</option>';
    
    Array.from(classSet).sort().forEach(cls => {
        const opt = document.createElement('option');
        opt.value = cls;
        opt.textContent = cls;
        if (cls === currentClass) opt.selected = true;
        classSelect.appendChild(opt);
    });

    instructorSelectedClass = classSelect.value;
    updateAssignmentDropdownOptions();
}

// Handle Course / Class Filter Change
function handleInstructorClassFilterChange() {
    const classSelect = document.getElementById('instructor-class-filter');
    instructorSelectedClass = classSelect ? classSelect.value : '';
    
    // Update assignment options based on newly selected class
    updateAssignmentDropdownOptions();
    renderInstructorTable();
}

// Handle Assignment Filter Change
function handleInstructorAssignmentFilterChange() {
    const assignSelect = document.getElementById('instructor-assignment-filter');
    instructorSelectedAssignment = assignSelect ? assignSelect.value : '';
    renderInstructorTable();
}

// Update Assignment Dropdown Options depending on selected Class (Single Select)
function updateAssignmentDropdownOptions() {
    const assignSelect = document.getElementById('instructor-assignment-filter');
    if (!assignSelect) return;

    const assignmentSet = new Set();

    if (instructorSelectedClass && submissionsConfigData && submissionsConfigData.config && submissionsConfigData.config[instructorSelectedClass]) {
        Object.keys(submissionsConfigData.config[instructorSelectedClass]).forEach(a => assignmentSet.add(a));
    } else {
        // Collect from all config and student records
        if (submissionsConfigData && submissionsConfigData.config) {
            Object.values(submissionsConfigData.config).forEach(assignObj => {
                Object.keys(assignObj).forEach(a => assignmentSet.add(a));
            });
        }
        instructorStudentsData.forEach(s => {
            if (s.latest_assignment && s.latest_assignment !== '--') {
                if (!instructorSelectedClass || s.latest_class === instructorSelectedClass) {
                    assignmentSet.add(s.latest_assignment);
                }
            }
        });
    }

    const uniqueAssignments = Array.from(assignmentSet).sort();
    const currentVal = assignSelect.value || instructorSelectedAssignment;

    assignSelect.innerHTML = '<option value="">All Assignments</option>';
    uniqueAssignments.forEach(assign => {
        const opt = document.createElement('option');
        opt.value = assign;
        opt.textContent = assign;
        if (assign === currentVal) opt.selected = true;
        assignSelect.appendChild(opt);
    });

    instructorSelectedAssignment = assignSelect.value;
}

// Reset All Instructor Filters
function resetInstructorFilters() {
    const studentSelect = document.getElementById('instructor-student-filter');
    const classSelect = document.getElementById('instructor-class-filter');
    const assignSelect = document.getElementById('instructor-assignment-filter');

    if (studentSelect) studentSelect.value = '';
    if (classSelect) classSelect.value = '';
    if (assignSelect) assignSelect.value = '';

    instructorSelectedStudent = '';
    instructorSelectedClass = '';
    instructorSelectedAssignment = '';

    updateAssignmentDropdownOptions();
    renderInstructorTable();
}

// Handle Interactive Column Sorting Toggle
function handleInstructorSort(columnName) {
    if (currentInstructorSort.column === columnName) {
        // Toggle order
        currentInstructorSort.order = currentInstructorSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentInstructorSort.column = columnName;
        // Default sort direction: descending for scores, time, total; ascending for text
        if (['highest_score', 'latest_score', 'latest_submission_time', 'total_submissions'].includes(columnName)) {
            currentInstructorSort.order = 'desc';
        } else {
            currentInstructorSort.order = 'asc';
        }
    }

    renderInstructorTable();
}

// Render Filtered & Sorted Instructor Table
function renderInstructorTable() {
    const tbody = document.getElementById('instructor-table-body');
    const summaryEl = document.getElementById('instructor-active-filter-summary');
    if (!tbody) return;

    // 1. Filter dataset
    let filtered = instructorStudentsData.filter(s => {
        // Filter by Single Student Name
        if (instructorSelectedStudent && s.student_name.trim().toLowerCase() !== instructorSelectedStudent.trim().toLowerCase()) {
            return false;
        }

        // Filter by Course / Class
        const studentClass = (s.latest_class || '').trim();
        if (instructorSelectedClass) {
            if (!studentClass || studentClass.toLowerCase() !== instructorSelectedClass.trim().toLowerCase()) {
                return false;
            }
        }

        // Filter by Single Assignment
        const studentAssign = (s.latest_assignment || '').trim();
        if (instructorSelectedAssignment) {
            if (!studentAssign || studentAssign.toLowerCase() !== instructorSelectedAssignment.trim().toLowerCase()) {
                return false;
            }
        }

        return true;
    });

    // 2. Sort dataset
    const col = currentInstructorSort.column;
    const isAsc = currentInstructorSort.order === 'asc';

    filtered.sort((a, b) => {
        let valA = a[col];
        let valB = b[col];

        // Fallbacks for null/undefined
        if (valA === null || valA === undefined) valA = (typeof valB === 'number') ? -Infinity : '';
        if (valB === null || valB === undefined) valB = (typeof valA === 'number') ? -Infinity : '';

        if (typeof valA === 'number' && typeof valB === 'number') {
            return isAsc ? valA - valB : valB - valA;
        }

        if (col === 'latest_submission_time') {
            const timeA = new Date(valA).getTime() || 0;
            const timeB = new Date(valB).getTime() || 0;
            return isAsc ? timeA - timeB : timeB - timeA;
        }

        // String comparison
        const strA = String(valA).toLowerCase();
        const strB = String(valB).toLowerCase();
        return isAsc ? strA.localeCompare(strB) : strB.localeCompare(strA);
    });

    // 3. Update Sort Indicator Icons
    ['student_name', 'latest_class', 'latest_assignment', 'highest_score', 'latest_score', 'latest_model_used', 'latest_submission_time', 'total_submissions'].forEach(c => {
        const iconEl = document.getElementById(`sort-icon-${c}`);
        if (iconEl) {
            if (currentInstructorSort.column === c) {
                iconEl.textContent = currentInstructorSort.order === 'asc' ? '▲' : '▼';
                iconEl.className = 'sort-icon active';
            } else {
                iconEl.textContent = '↕';
                iconEl.className = 'sort-icon';
            }
        }
    });

    // 4. Update Statistics Cards based on filtered data
    const totalStudentsEl = document.getElementById('stat-total-students');
    const totalSubsEl = document.getElementById('stat-total-subs');
    const topScoreEl = document.getElementById('stat-top-score');

    if (totalStudentsEl) totalStudentsEl.textContent = filtered.length;
    if (totalSubsEl) totalSubsEl.textContent = filtered.reduce((acc, s) => acc + s.total_submissions, 0);
    if (topScoreEl) {
        const topScore = filtered.length > 0 ? Math.max(...filtered.map(s => s.highest_score)) : 0;
        topScoreEl.textContent = `${topScore.toFixed(1)}%`;
    }

    if (summaryEl) {
        summaryEl.textContent = `Showing ${filtered.length} of ${instructorStudentsData.length} students`;
    }

    // 5. Render Table Rows
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center" style="padding: 30px; color: var(--text-muted);">No submissions match the selected student and course/assignment filters.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    filtered.forEach(s => {
        const row = document.createElement('tr');
        const formattedTime = s.latest_submission_time ? new Date(s.latest_submission_time).toLocaleString() : '--';
        const modelName = s.latest_model_used || 'Gemini AI';
        const className = s.latest_class ? s.latest_class.trim() : '';
        const assignName = s.latest_assignment ? s.latest_assignment.trim() : '';
        
        const classHtml = className 
            ? `<span style="font-size: 0.78rem; font-weight: 600; color: #cbd5e1; background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.08);">🎓 ${escapeHtml(className)}</span>`
            : `<span style="color: var(--text-muted); font-size: 0.78rem;">--</span>`;

        const assignHtml = assignName 
            ? `<span style="font-size: 0.78rem; font-weight: 600; color: #a78bfa; background: rgba(167,139,250,0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(167,139,250,0.25);">📝 ${escapeHtml(assignName)}</span>`
            : `<span style="color: var(--text-muted); font-size: 0.78rem;">--</span>`;

        row.innerHTML = `
            <td>
                <a href="javascript:void(0)" class="student-link" onclick="openStudentModal('${escapeHtml(s.student_name)}')">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    <strong>${escapeHtml(s.student_name)}</strong>
                </a>
            </td>
            <td>${classHtml}</td>
            <td>${assignHtml}</td>
            <td>
                <span class="criterion-badge ${s.highest_score >= 80 ? 'badge-pass' : (s.highest_score >= 60 ? 'badge-partial' : 'badge-fail')}" style="font-size: 0.85rem;">
                    ${s.highest_score.toFixed(1)}% (${s.highest_grade})
                </span>
            </td>
            <td>
                <span class="criterion-badge ${s.latest_score >= 80 ? 'badge-pass' : (s.latest_score >= 60 ? 'badge-partial' : 'badge-fail')}">
                    ${s.latest_score.toFixed(1)}% (${s.latest_grade})
                </span>
            </td>
            <td>
                <span style="font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; background: rgba(99, 102, 241, 0.1); color: #818cf8; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(99,102,241,0.2);">
                    🤖 ${escapeHtml(modelName)}
                </span>
            </td>
            <td><small style="color: var(--text-muted);">${formattedTime}</small></td>
            <td><span style="font-weight: 700; color: #f8fafc;">${s.total_submissions}</span></td>
            <td>
                <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="openStudentModal('${escapeHtml(s.student_name)}')">
                    View Submissions
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}



// State for Gemini Traces Viewer 2-Box Layout
let cachedTraceSessions = [];
let currentSelectedSession = null;
let currentTraceEvents = [];
let currentTraceFilter = 'ALL';

// Load Gemini Telemetry Traces (Submissions in Top Box & Events in Bottom Box)
async function loadTracesData() {
    const tableBody = document.getElementById('traces-submissions-table-body');
    const countBadge = document.getElementById('traces-submission-count');
    const eventsContainer = document.getElementById('traces-events-container');

    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding: 24px;">Fetching submission traces from outputs/gemini_traces.jsonl...</td></tr>';
    }

    try {
        const response = await fetch('/api/traces/submissions?limit=100');
        const data = await response.json();
        cachedTraceSessions = data.sessions || [];

        if (countBadge) {
            countBadge.textContent = `${cachedTraceSessions.length} submission${cachedTraceSessions.length === 1 ? '' : 's'}`;
        }

        if (cachedTraceSessions.length === 0) {
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding: 30px; color: var(--text-muted);">No telemetry traces recorded yet. Run a grading evaluation to generate traces.</td></tr>';
            }
            if (eventsContainer) {
                eventsContainer.innerHTML = '<div class="text-center" style="padding: 40px; color: var(--text-muted);">No traces found. Submit a repository for grading first.</div>';
            }
            return;
        }

        // Render Top Box (Submissions Table)
        renderTraceSubmissionsTable();

        // Automatically select the first (latest) submission
        if (cachedTraceSessions.length > 0) {
            selectTraceSubmission(cachedTraceSessions[0].trace_id);
        }

    } catch (err) {
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--danger); padding: 20px;">Error loading traces: ${escapeHtml(err.message)}</td></tr>`;
        }
    }
}

// Render Top Box: Submissions Table
function renderTraceSubmissionsTable() {
    const tableBody = document.getElementById('traces-submissions-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    cachedTraceSessions.forEach((session, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'trace-row';
        tr.id = `trace-row-${session.trace_id}`;
        tr.onclick = () => selectTraceSubmission(session.trace_id);

        const timeStr = session.start_time ? new Date(session.start_time).toLocaleString() : '--';
        
        let scoreHtml = '<span style="color: var(--text-muted); font-size: 0.8rem;">In Progress...</span>';
        if (session.overall_score !== null && session.overall_score !== undefined) {
            const scoreVal = Number(session.overall_score);
            const gradeLetter = session.letter_grade || '';
            const color = scoreVal >= 80 ? 'var(--success)' : (scoreVal >= 60 ? 'var(--warning)' : 'var(--danger)');
            scoreHtml = `<span style="font-weight: 700; color: ${color};">${scoreVal.toFixed(1)}%</span> <span class="grade-badge" style="font-size: 0.68rem; padding: 2px 6px; margin-left: 4px;">${gradeLetter}</span>`;
        }

        const modelDisplay = session.model_name || 'Google Gemini';

        tr.innerHTML = `
            <td>
                <strong style="color: #f8fafc; font-size: 0.88rem;">${escapeHtml(session.student_name)}</strong>
            </td>
            <td>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--text-muted); max-width: 260px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(session.folder_name)}">
                    ${escapeHtml(session.folder_name)}
                </span>
            </td>
            <td>
                <span style="font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; background: rgba(99,102,241,0.15); color: #818cf8; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(99,102,241,0.25);">
                    🤖 ${escapeHtml(modelDisplay)}
                </span>
            </td>
            <td>${scoreHtml}</td>
            <td style="font-size: 0.8rem; color: var(--text-muted);">${timeStr}</td>
            <td>
                <span style="font-size: 0.76rem; background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 10px; color: #94a3b8; font-weight: 600;">
                    ${session.event_count || session.events.length} events
                </span>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

// Select a Submission & Load Events in Bottom Box
function selectTraceSubmission(traceId) {
    const session = cachedTraceSessions.find(s => s.trace_id === traceId);
    if (!session) return;

    currentSelectedSession = session;
    currentTraceEvents = session.events || [];

    // Highlight selected row in Top Box
    document.querySelectorAll('.trace-row').forEach(row => row.classList.remove('active-trace-row'));
    const activeRow = document.getElementById(`trace-row-${traceId}`);
    if (activeRow) {
        activeRow.classList.add('active-trace-row');
    }

    // Update Bottom Box Headers
    const titleEl = document.getElementById('selected-trace-title');
    const badgeEl = document.getElementById('selected-trace-badge');
    const subtitleEl = document.getElementById('selected-trace-subtitle');

    if (titleEl) {
        titleEl.innerHTML = `
            <span>🔍 Trace Events: <span style="color: #60a5fa;">${escapeHtml(session.student_name)}</span></span>
        `;
    }

    if (badgeEl) {
        if (session.overall_score !== null && session.overall_score !== undefined) {
            badgeEl.textContent = `${Number(session.overall_score).toFixed(1)}% (${session.letter_grade || '--'})`;
            badgeEl.style.background = session.overall_score >= 80 ? 'rgba(16,185,129,0.15)' : (session.overall_score >= 60 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)');
            badgeEl.style.color = session.overall_score >= 80 ? '#34d399' : (session.overall_score >= 60 ? '#fbbf24' : '#f87171');
        } else {
            badgeEl.textContent = session.status || 'Active';
            badgeEl.style.background = 'rgba(99,102,241,0.15)';
            badgeEl.style.color = '#818cf8';
        }
    }

    if (subtitleEl) {
        const timeStr = session.start_time ? new Date(session.start_time).toLocaleString() : '--';
        subtitleEl.innerHTML = `Target: <code>${escapeHtml(session.folder_name)}</code> &bull; Model: <strong>${escapeHtml(session.model_name)}</strong> &bull; Started: ${timeStr} &bull; Trace ID: <code>${escapeHtml(session.trace_id)}</code>`;
    }

    // Reset filter pill to ALL
    currentTraceFilter = 'ALL';
    document.querySelectorAll('.trace-pill').forEach(btn => btn.classList.remove('active'));
    const allBtn = document.querySelector('.trace-pill');
    if (allBtn) allBtn.classList.add('active');

    // Render Events in Bottom Box
    renderTraceEvents(currentTraceEvents);
}

// Filter Events by Type
function filterTraceEvents(filterType, event) {
    currentTraceFilter = filterType;
    if (event && event.target) {
        document.querySelectorAll('.trace-pill').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
    }

    if (!currentSelectedSession) return;

    if (filterType === 'ALL') {
        renderTraceEvents(currentTraceEvents);
    } else if (filterType === 'TOOL') {
        const filtered = currentTraceEvents.filter(e => e.event_type === 'TOOL_INVOCATION' || e.event_type === 'TOOL_RESPONSE');
        renderTraceEvents(filtered);
    } else {
        const filtered = currentTraceEvents.filter(e => e.event_type === filterType);
        renderTraceEvents(filtered);
    }
}

// Render Events in Bottom Box Container
function renderTraceEvents(events) {
    const container = document.getElementById('traces-events-container');
    if (!container) return;

    if (!events || events.length === 0) {
        container.innerHTML = '<div class="text-center" style="padding: 40px; color: var(--text-muted);">No events match the selected filter.</div>';
        return;
    }

    container.innerHTML = '';
    events.forEach((ev, idx) => {
        const card = document.createElement('div');
        const evType = ev.event_type || 'EVENT';
        const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '';
        const dur = ev.duration_ms ? `${ev.duration_ms.toFixed(1)} ms` : (ev.details && ev.details.duration_ms ? `${ev.details.duration_ms.toFixed(1)} ms` : '');
        const details = ev.details || {};
        const cardId = `log-detail-${idx}`;

        let cardTypeClass = 'event-lifecycle';
        let badgeClass = 'badge-pass';
        let typeIcon = '📌';

        if (evType === 'MODEL_CALL') {
            cardTypeClass = 'event-model-call';
            badgeClass = 'badge-partial';
            typeIcon = '🤖';
        } else if (evType === 'MODEL_RESPONSE') {
            cardTypeClass = 'event-model-response';
            badgeClass = 'badge-pass';
            typeIcon = '⚡';
        } else if (evType === 'SKILL_USAGE') {
            cardTypeClass = 'event-skill';
            badgeClass = 'badge-pass';
            typeIcon = '🛠️';
        } else if (evType.startsWith('TOOL')) {
            cardTypeClass = 'event-tool';
            badgeClass = 'badge-partial';
            typeIcon = '🔧';
        } else if (evType === 'TRACE_START' || evType === 'TRACE_END') {
            cardTypeClass = 'event-lifecycle';
            badgeClass = 'badge-pass';
            typeIcon = '🏁';
        }

        card.className = `trace-event-card ${cardTypeClass}`;

        let detailHtml = '';

        if (evType === 'MODEL_CALL') {
            detailHtml = `
                <div style="font-size: 0.82rem; color: #93c5fd; margin-bottom: 6px;">
                    <strong>Model:</strong> <code>${escapeHtml(details.model || 'Gemini')}</code> &bull; 
                    <strong>Prompt Length:</strong> ${details.prompt_length_chars || 0} characters
                </div>
                <div style="font-size: 0.78rem; color: var(--text-muted); background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px; font-family: 'JetBrains Mono', monospace;">
                    ${escapeHtml(details.prompt_preview || 'Prompt sent to Gemini API')}
                </div>
                ${details.full_prompt ? `
                    <button class="raw-log-toggle" onclick="toggleLogContent('${cardId}')">
                        <span>📄 View Full Prompt Payload</span>
                    </button>
                    <div id="${cardId}" class="hidden" style="margin-top: 8px;">
                        <pre style="background: rgba(0,0,0,0.5); padding: 12px; border-radius: 6px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; max-height: 240px; overflow-y: auto; color: #93c5fd; white-space: pre-wrap;">${escapeHtml(details.full_prompt)}</pre>
                    </div>
                ` : ''}
            `;
        } else if (evType === 'MODEL_RESPONSE') {
            const tokens = details.usage_metadata ? `Prompt: ${details.usage_metadata.prompt_token_count || 0} &bull; Candidates: ${details.usage_metadata.candidates_token_count || 0} &bull; Total: ${details.usage_metadata.total_token_count || 0} tokens` : '';
            detailHtml = `
                <div style="font-size: 0.82rem; color: #86efac; margin-bottom: 6px;">
                    <strong>Status:</strong> HTTP ${details.status_code || 200} OK &bull; 
                    <strong>Model:</strong> <code>${escapeHtml(details.model || 'Gemini')}</code>
                    ${tokens ? ` &bull; <span>${tokens}</span>` : ''}
                </div>
                <div style="font-size: 0.78rem; color: var(--text-muted); background: rgba(0,0,0,0.25); padding: 8px; border-radius: 6px; font-family: 'JetBrains Mono', monospace;">
                    ${escapeHtml(details.response_preview || 'Gemini evaluation response received')}
                </div>
                ${details.full_response ? `
                    <button class="raw-log-toggle" onclick="toggleLogContent('${cardId}')">
                        <span>📊 View Raw Model Response JSON</span>
                    </button>
                    <div id="${cardId}" class="hidden" style="margin-top: 8px;">
                        <pre style="background: rgba(0,0,0,0.5); padding: 12px; border-radius: 6px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; max-height: 240px; overflow-y: auto; color: #86efac; white-space: pre-wrap;">${escapeHtml(JSON.stringify(details.full_response, null, 2))}</pre>
                    </div>
                ` : ''}
            `;
        } else if (evType === 'SKILL_USAGE') {
            detailHtml = `
                <div style="font-size: 0.82rem; color: #d8b4fe; margin-bottom: 6px;">
                    <strong>Skill:</strong> <code>${escapeHtml(details.skill_name || 'SpecParser')}</code> &bull; 
                    <strong>Status:</strong> ${escapeHtml(details.status || 'SUCCESS')}
                </div>
                <pre style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px; font-size: 0.76rem; font-family: 'JetBrains Mono', monospace; color: #cbd5e1; margin: 0;">${escapeHtml(JSON.stringify({ inputs: details.inputs, outputs: details.outputs }, null, 2))}</pre>
            `;
        } else if (evType === 'TRACE_START') {
            detailHtml = `
                <div style="font-size: 0.82rem; color: #c7d2fe;">
                    <strong>Initialized Trace:</strong> Evaluating <strong>${escapeHtml(details.student_name || '')}</strong> &bull; Target: <code>${escapeHtml(details.folder_name || '')}</code>
                </div>
            `;
        } else if (evType === 'TRACE_END') {
            detailHtml = `
                <div style="font-size: 0.82rem; color: #86efac; margin-bottom: 4px;">
                    <strong>Grading Completed:</strong> Score: <strong>${details.overall_score}% (${details.letter_grade})</strong>
                </div>
                <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(details.summary || '')}</div>
            `;
        } else {
            detailHtml = `
                <pre style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px; font-size: 0.76rem; font-family: 'JetBrains Mono', monospace; color: #cbd5e1; margin: 0;">${escapeHtml(JSON.stringify(details, null, 2))}</pre>
            `;
        }

        card.innerHTML = `
            <div class="trace-event-header">
                <div>
                    <span style="margin-right: 6px;">${typeIcon}</span>
                    <span class="criterion-badge ${badgeClass}" style="font-size: 0.76rem; font-weight: 700;">${evType}</span>
                    ${dur ? `<span style="margin-left: 8px; font-size: 0.78rem; color: #38bdf8; font-weight: 600;">⚡ ${dur}</span>` : ''}
                </div>
                <span style="font-size: 0.76rem; color: var(--text-muted);">${timeStr}</span>
            </div>
            ${detailHtml}
        `;

        container.appendChild(card);
    });
}

// Toggle Collapsible Log Payloads
function toggleLogContent(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.classList.toggle('hidden');
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
            const modelName = sub.model_used || (details && details.model_used) || 'Gemini AI';
            const item = document.createElement('div');
            item.className = 'history-item';
            
            let criteriaHtml = '';
            if (details && details.criteria) {
                criteriaHtml = `
                    <div style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
                        ${details.criteria.map(c => {
                            const isPerf = c.earned_score >= c.max_score;
                            const isMand = c.is_mandatory || c.category === 'Mandatory Requirement';
                            return `
                                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                        <div>
                                            ${isMand ? '<span style="font-size: 0.68rem; color: #f87171; font-weight: 700; margin-right: 4px;">[MANDATORY]</span>' : ''}
                                            <strong style="font-size: 0.82rem;">${escapeHtml(c.title)}</strong>
                                        </div>
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
                        <span style="margin-left: 8px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; background: rgba(99,102,241,0.15); color: #818cf8; padding: 2px 6px; border-radius: 4px;">
                            ${escapeHtml(modelName)}
                        </span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 0.8rem; color: var(--text-muted);">${timeStr}</span>
                        <a href="/api/submissions/${sub.id}/report" target="_blank" class="btn btn-secondary" style="padding: 3px 8px; font-size: 0.75rem; color: #c7d2fe;">
                            🖨️ View/Print
                        </a>
                        <a href="/api/submissions/${sub.id}/download/pdf" class="btn btn-secondary" style="padding: 3px 8px; font-size: 0.75rem;">
                            PDF
                        </a>
                        <a href="/api/submissions/${sub.id}/download/txt" class="btn btn-secondary" style="padding: 3px 8px; font-size: 0.75rem;">
                            TXT
                        </a>
                    </div>
                </div>
                <div class="history-folder">
                    <span>Folder: ${escapeHtml(sub.folder_name)}</span>
                    ${(sub.class_name || (details && details.class_name)) ? `<span style="margin-left: 8px; font-size: 0.75rem; background: rgba(255,255,255,0.06); color: #cbd5e1; padding: 2px 6px; border-radius: 4px;">🎓 ${escapeHtml(sub.class_name || (details && details.class_name))}</span>` : ''}
                    ${(sub.assignment_name || (details && details.assignment_name)) ? `<span style="margin-left: 6px; font-size: 0.75rem; background: rgba(167,139,250,0.15); color: #a78bfa; padding: 2px 6px; border-radius: 4px;">📝 ${escapeHtml(sub.assignment_name || (details && details.assignment_name))}</span>` : ''}
                </div>
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

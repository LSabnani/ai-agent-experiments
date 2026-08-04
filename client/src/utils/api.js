const API_BASE = '/api';

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || `Request failed with status ${res.status}`);
  }

  return data;
}

export async function cloneRepo(repoUrl) {
  return request('/repo/clone', {
    method: 'POST',
    body: JSON.stringify({ repoUrl }),
  });
}

export async function getBranches() {
  return request('/repo/branches');
}

export async function getClasses() {
  return request('/repo/classes');
}

export async function getClassCriteria(classId) {
  return request(`/repo/class/${classId}/criteria`);
}

export async function gradeStudent(branch, classId) {
  return request('/grade/student', {
    method: 'POST',
    body: JSON.stringify({ branch, classId }),
  });
}

export async function gradeBatch(branches, classId) {
  return request('/grade/batch', {
    method: 'POST',
    body: JSON.stringify({ branches, classId }),
  });
}

export async function getGradeResults() {
  return request('/grade/results');
}

export async function clearGradeCache() {
  return request('/grade/cache', { method: 'DELETE' });
}

export async function healthCheck() {
  return request('/health');
}

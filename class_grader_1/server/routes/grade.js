import { Router } from 'express';
import { checkoutBranch, getCachedRepoPath } from '../services/gitService.js';
import {
  getHomework,
  getGradingCriteria,
  getGoldenSolution,
  getStudentSubmission,
} from '../services/courseService.js';
import { gradeSubmission } from '../services/gradingService.js';

const router = Router();

// In-memory cache of grading results
const gradingCache = new Map();

/**
 * POST /api/grade/student
 * Grades a single student (branch) for a specific class.
 * Body: { branch: string, classId: string }
 */
router.post('/student', async (req, res) => {
  try {
    const { branch, classId } = req.body;

    if (!branch || !classId) {
      return res.status(400).json({ error: 'branch and classId are required' });
    }

    const repoPath = getCachedRepoPath();
    if (!repoPath) {
      return res.status(400).json({ error: 'No repository cloned yet.' });
    }

    // Check cache
    const cacheKey = `${branch}:${classId}`;
    if (gradingCache.has(cacheKey)) {
      return res.json({
        success: true,
        cached: true,
        result: gradingCache.get(cacheKey),
      });
    }

    console.log(`Grading ${branch} for ${classId}...`);

    // 1. Checkout the student's branch
    await checkoutBranch(repoPath, branch);

    // 2. Load all grading materials
    const [homework, gradingCriteria, goldenSolutionFiles, studentSubmission] =
      await Promise.all([
        getHomework(repoPath, classId),
        getGradingCriteria(repoPath, classId),
        getGoldenSolution(repoPath, classId),
        getStudentSubmission(repoPath, classId),
      ]);

    if (studentSubmission.files.length === 0) {
      return res.json({
        success: true,
        result: {
          branch,
          classId,
          criteria: [],
          overallVerdict: 'needs_revision',
          revisionPriority: 'No submission found for this class.',
          summary: `No files found in the student's submission directory for ${classId}. The student may not have submitted work for this class yet.`,
          verdictCounts: { met: 0, partial: 0, not_met: 0 },
          noSubmission: true,
        },
      });
    }

    // 3. Grade with Claude
    const result = await gradeSubmission({
      studentFiles: studentSubmission.files,
      goldenSolutionFiles,
      gradingCriteria,
      homework,
      classId,
    });

    // Attach metadata
    result.branch = branch;
    result.classId = classId;
    result.studentFileCount = studentSubmission.files.length;
    result.gradedAt = new Date().toISOString();

    // Cache the result
    gradingCache.set(cacheKey, result);

    res.json({ success: true, cached: false, result });
  } catch (err) {
    console.error('Grading error:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /api/grade/batch
 * Grades multiple students (branches) for a specific class.
 * Body: { branches: string[], classId: string }
 * Returns results as they complete.
 */
router.post('/batch', async (req, res) => {
  try {
    const { branches, classId } = req.body;

    if (!branches || !Array.isArray(branches) || branches.length === 0 || !classId) {
      return res.status(400).json({ error: 'branches (array) and classId are required' });
    }

    const repoPath = getCachedRepoPath();
    if (!repoPath) {
      return res.status(400).json({ error: 'No repository cloned yet.' });
    }

    // Pre-load the shared grading materials (same for all students in a class)
    const [homework, gradingCriteria, goldenSolutionFiles] = await Promise.all([
      getHomework(repoPath, classId),
      getGradingCriteria(repoPath, classId),
      getGoldenSolution(repoPath, classId),
    ]);

    const results = [];

    // Grade students sequentially (to avoid git checkout conflicts)
    for (const branch of branches) {
      const cacheKey = `${branch}:${classId}`;

      // Check cache first
      if (gradingCache.has(cacheKey)) {
        results.push({ branch, cached: true, result: gradingCache.get(cacheKey) });
        continue;
      }

      try {
        console.log(`Batch grading: ${branch} for ${classId}...`);

        // Checkout student branch
        await checkoutBranch(repoPath, branch);

        // Get student submission
        const studentSubmission = await getStudentSubmission(repoPath, classId);

        if (studentSubmission.files.length === 0) {
          const noSubResult = {
            branch,
            classId,
            criteria: [],
            overallVerdict: 'needs_revision',
            revisionPriority: 'No submission found.',
            summary: `No files found for ${classId}.`,
            verdictCounts: { met: 0, partial: 0, not_met: 0 },
            noSubmission: true,
            gradedAt: new Date().toISOString(),
          };
          gradingCache.set(cacheKey, noSubResult);
          results.push({ branch, cached: false, result: noSubResult });
          continue;
        }

        // Grade with Claude
        const result = await gradeSubmission({
          studentFiles: studentSubmission.files,
          goldenSolutionFiles,
          gradingCriteria,
          homework,
          classId,
        });

        result.branch = branch;
        result.classId = classId;
        result.studentFileCount = studentSubmission.files.length;
        result.gradedAt = new Date().toISOString();

        gradingCache.set(cacheKey, result);
        results.push({ branch, cached: false, result });
      } catch (err) {
        console.error(`Error grading ${branch}:`, err.message);
        results.push({
          branch,
          cached: false,
          result: {
            branch,
            classId,
            criteria: [],
            overallVerdict: 'needs_revision',
            revisionPriority: `Grading error: ${err.message}`,
            summary: `Failed to grade: ${err.message}`,
            verdictCounts: { met: 0, partial: 0, not_met: 0 },
            error: true,
          },
        });
      }
    }

    res.json({ success: true, results });
  } catch (err) {
    console.error('Batch grading error:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /api/grade/results
 * Returns all cached grading results.
 */
router.get('/results', (req, res) => {
  const results = Array.from(gradingCache.entries()).map(([key, result]) => ({
    key,
    ...result,
  }));
  res.json({ results });
});

/**
 * DELETE /api/grade/cache
 * Clears the grading cache.
 */
router.delete('/cache', (req, res) => {
  gradingCache.clear();
  res.json({ success: true, message: 'Grading cache cleared' });
});

export default router;

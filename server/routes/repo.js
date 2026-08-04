import { Router } from 'express';
import { cloneRepo, listBranches, checkoutBranch, getCachedRepoPath } from '../services/gitService.js';
import { getClasses, getHomework, getGradingCriteria } from '../services/courseService.js';

const router = Router();

/**
 * POST /api/repo/clone
 * Clones a GitHub repository and returns available classes + branches.
 * Body: { repoUrl: string }
 */
router.post('/clone', async (req, res) => {
  try {
    const { repoUrl } = req.body;

    if (!repoUrl) {
      return res.status(400).json({ error: 'repoUrl is required' });
    }

    // Basic URL validation
    if (!repoUrl.match(/^https?:\/\/(www\.)?github\.com\/.+\/.+/)) {
      return res.status(400).json({ error: 'Please provide a valid GitHub repository URL' });
    }

    console.log(`Cloning repo: ${repoUrl}`);
    const repoPath = await cloneRepo(repoUrl);

    // Get available classes and branches in parallel
    const [classes, branches] = await Promise.all([
      getClasses(repoPath),
      listBranches(repoPath),
    ]);

    res.json({
      success: true,
      repoPath,
      classes,
      branches,
    });
  } catch (err) {
    console.error('Clone error:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /api/repo/branches
 * Returns the list of branches for the currently cloned repo.
 */
router.get('/branches', async (req, res) => {
  try {
    const repoPath = getCachedRepoPath();
    if (!repoPath) {
      return res.status(400).json({ error: 'No repository cloned yet. Clone a repo first.' });
    }

    const branches = await listBranches(repoPath);
    res.json({ branches });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /api/repo/classes
 * Returns available classes with their readiness status.
 */
router.get('/classes', async (req, res) => {
  try {
    const repoPath = getCachedRepoPath();
    if (!repoPath) {
      return res.status(400).json({ error: 'No repository cloned yet.' });
    }

    const classes = await getClasses(repoPath);
    res.json({ classes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /api/repo/class/:classId/criteria
 * Returns homework.md and GRADING.md for a specific class.
 */
router.get('/class/:classId/criteria', async (req, res) => {
  try {
    const repoPath = getCachedRepoPath();
    if (!repoPath) {
      return res.status(400).json({ error: 'No repository cloned yet.' });
    }

    const { classId } = req.params;
    const [homework, gradingCriteria] = await Promise.all([
      getHomework(repoPath, classId),
      getGradingCriteria(repoPath, classId),
    ]);

    res.json({ homework, gradingCriteria });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

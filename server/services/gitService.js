import simpleGit from 'simple-git';
import path from 'path';
import crypto from 'crypto';
import fs from 'fs/promises';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPOS_DIR = path.join(__dirname, '..', '.repos');

// In-memory cache of cloned repo info
let cachedRepo = null;

/**
 * Clones a public GitHub repository into .repos/<hash>/.
 * Returns the local path to the cloned repo.
 */
export async function cloneRepo(repoUrl) {
  // Create a deterministic directory name from the URL
  const hash = crypto.createHash('md5').update(repoUrl).digest('hex').slice(0, 12);
  const repoPath = path.join(REPOS_DIR, hash);

  // Ensure the repos directory exists
  await fs.mkdir(REPOS_DIR, { recursive: true });

  // Check if already cloned
  try {
    await fs.access(path.join(repoPath, '.git'));
    console.log(`Repo already cloned at ${repoPath}, pulling latest...`);
    const git = simpleGit(repoPath);
    await git.fetch(['--all']);
    cachedRepo = { url: repoUrl, path: repoPath };
    return repoPath;
  } catch {
    // Not yet cloned — proceed
  }

  // Remove any partial clone
  try {
    await fs.rm(repoPath, { recursive: true, force: true });
  } catch { /* ignore */ }

  console.log(`Cloning ${repoUrl} to ${repoPath}...`);
  const git = simpleGit();
  await git.clone(repoUrl, repoPath);

  cachedRepo = { url: repoUrl, path: repoPath };
  return repoPath;
}

/**
 * Lists all remote branches (excluding HEAD), returning branch names.
 * Each branch typically represents a student's fork.
 */
export async function listBranches(repoPath) {
  const git = simpleGit(repoPath);

  // Fetch all remote branches
  await git.fetch(['--all']);

  const branchSummary = await git.branch(['-r']);
  const branches = branchSummary.all
    .filter(b => !b.includes('HEAD'))
    .map(b => {
      // Remote branches look like "origin/branch-name"
      const parts = b.split('/');
      return {
        full: b.trim(),
        name: parts.slice(1).join('/'),
        remote: parts[0],
      };
    })
    // Filter out 'main' and 'master' — those are the upstream, not student submissions
    .filter(b => b.name !== 'main' && b.name !== 'master');

  return branches;
}

/**
 * Checks out a specific branch.
 */
export async function checkoutBranch(repoPath, branchName) {
  const git = simpleGit(repoPath);

  try {
    // Try to checkout a local tracking branch
    await git.checkout(branchName);
  } catch {
    // Create a local tracking branch from the remote
    try {
      await git.checkout(['-b', branchName, `origin/${branchName}`]);
    } catch {
      // Branch may already exist locally, force checkout
      await git.checkout(['-f', branchName]);
    }
  }
}

/**
 * Returns the cached repo path, or null if no repo is cloned.
 */
export function getCachedRepoPath() {
  return cachedRepo?.path || null;
}

/**
 * Returns the cached repo info.
 */
export function getCachedRepo() {
  return cachedRepo;
}

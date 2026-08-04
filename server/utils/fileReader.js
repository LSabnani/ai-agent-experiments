import fs from 'fs/promises';
import path from 'path';

// File extensions to include when reading code submissions
const CODE_EXTENSIONS = new Set([
  '.py', '.md', '.yaml', '.yml', '.toml', '.sh', '.bash',
  '.js', '.ts', '.jsx', '.tsx', '.json',
  '.html', '.css', '.txt', '.cfg', '.ini', '.env.example',
]);

// Directories to always skip
const SKIP_DIRS = new Set([
  '.git', 'node_modules', '.venv', '__pycache__', '.mypy_cache',
  '.pytest_cache', '.ruff_cache', 'dist', 'build', '.eggs',
  '*.egg-info', '.tox',
]);

/**
 * Recursively reads all code files in a directory.
 * Returns an array of { relativePath, content, language }.
 */
export async function readCodeFiles(dirPath, basePath = null) {
  if (!basePath) basePath = dirPath;

  const results = [];

  let entries;
  try {
    entries = await fs.readdir(dirPath, { withFileTypes: true });
  } catch (err) {
    console.error(`Cannot read directory: ${dirPath}`, err.message);
    return results;
  }

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    const relativePath = path.relative(basePath, fullPath);

    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name) || entry.name.endsWith('.egg-info')) {
        continue;
      }
      const subFiles = await readCodeFiles(fullPath, basePath);
      results.push(...subFiles);
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name).toLowerCase();
      if (CODE_EXTENSIONS.has(ext) || entry.name === '.gitignore') {
        try {
          const content = await fs.readFile(fullPath, 'utf-8');
          results.push({
            relativePath,
            content,
            language: getLanguage(ext),
          });
        } catch (err) {
          console.error(`Cannot read file: ${fullPath}`, err.message);
        }
      }
    }
  }

  return results;
}

/**
 * Maps file extension to a language identifier.
 */
function getLanguage(ext) {
  const map = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'jsx',
    '.tsx': 'tsx',
    '.md': 'markdown',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.sh': 'shell',
    '.bash': 'shell',
    '.json': 'json',
    '.html': 'html',
    '.css': 'css',
    '.txt': 'text',
    '.cfg': 'ini',
    '.ini': 'ini',
  };
  return map[ext] || 'text';
}

/**
 * Reads a single file and returns its content, or null if not found.
 */
export async function readFileContent(filePath) {
  try {
    return await fs.readFile(filePath, 'utf-8');
  } catch (err) {
    return null;
  }
}

/**
 * Checks if a directory exists.
 */
export async function dirExists(dirPath) {
  try {
    const stat = await fs.stat(dirPath);
    return stat.isDirectory();
  } catch {
    return false;
  }
}

import path from 'path';
import fs from 'fs/promises';
import { readCodeFiles, readFileContent, dirExists } from '../utils/fileReader.js';

// The known path structure within the agent_engineering repo
const CLASSES_BASE = 'agent-engineering-book/Gemini/1-Foundations/Classes';
const STUDENT_WORK_BASE = 'my-work';

// Class metadata — derived from the course README
const CLASS_TOPICS = {
  'class-01': 'Foundations, WidgetWare Spec & Repository Harness',
  'class-02': 'Gemini Context and Instruction Architecture',
  'class-03': 'First ADK Agent (Embedded Procedure)',
  'class-04': 'Skills and Reusable Agent Capabilities',
  'class-05': 'Structured Outputs and Agent Contracts',
  'class-06': 'Tool Engineering',
  'class-07': 'MCP and Evidence-Backed Research',
  'class-08': 'Multi-Agent Workflow and Human Approval',
  'class-09': 'Evaluate, Deploy, and Demonstrate',
  'class-10': 'Loop Engineering with ADK',
};

/**
 * Scans the repo for available classes (class-01 through class-10).
 * Returns an array of class objects with id, topic, and availability flags.
 */
export async function getClasses(repoPath) {
  const classesDir = path.join(repoPath, CLASSES_BASE);
  const classes = [];

  for (const [classId, topic] of Object.entries(CLASS_TOPICS)) {
    const classDir = path.join(classesDir, classId);
    const hasHomework = await readFileContent(path.join(classDir, 'homework.md')) !== null;
    const hasGrading = await readFileContent(path.join(classDir, 'GRADING.md')) !== null;
    const hasGoldenSolution = await dirExists(path.join(classDir, 'golden-solution'));

    classes.push({
      id: classId,
      number: parseInt(classId.replace('class-', ''), 10),
      topic,
      hasHomework,
      hasGrading,
      hasGoldenSolution,
      ready: hasHomework && hasGrading && hasGoldenSolution,
    });
  }

  return classes;
}

/**
 * Reads the homework.md for a specific class.
 */
export async function getHomework(repoPath, classId) {
  const filePath = path.join(repoPath, CLASSES_BASE, classId, 'homework.md');
  const content = await readFileContent(filePath);
  if (!content) {
    throw new Error(`homework.md not found for ${classId}`);
  }
  return content;
}

/**
 * Reads the GRADING.md for a specific class.
 */
export async function getGradingCriteria(repoPath, classId) {
  const filePath = path.join(repoPath, CLASSES_BASE, classId, 'GRADING.md');
  const content = await readFileContent(filePath);
  if (!content) {
    throw new Error(`GRADING.md not found for ${classId}`);
  }
  return content;
}

/**
 * Reads the GRADING-RUBRIC-TEMPLATE.md (shared across all classes).
 */
export async function getGradingTemplate(repoPath) {
  const filePath = path.join(repoPath, CLASSES_BASE, 'GRADING-RUBRIC-TEMPLATE.md');
  const content = await readFileContent(filePath);
  if (!content) {
    throw new Error('GRADING-RUBRIC-TEMPLATE.md not found');
  }
  return content;
}

/**
 * Reads all code files from the golden solution for a class.
 */
export async function getGoldenSolution(repoPath, classId) {
  const goldenDir = path.join(repoPath, CLASSES_BASE, classId, 'golden-solution');
  if (!(await dirExists(goldenDir))) {
    throw new Error(`Golden solution not found for ${classId}`);
  }
  return await readCodeFiles(goldenDir);
}

/**
 * Reads all code files from a student's submission for a class.
 * Looks in multiple possible locations:
 *   1. my-work/class-0N/
 *   2. my-work/gemini-book-1/class-0N/
 */
export async function getStudentSubmission(repoPath, classId) {
  const possiblePaths = [
    path.join(repoPath, STUDENT_WORK_BASE, classId),
    path.join(repoPath, STUDENT_WORK_BASE, 'gemini-book-1', classId),
  ];

  for (const submissionDir of possiblePaths) {
    if (await dirExists(submissionDir)) {
      const files = await readCodeFiles(submissionDir);
      if (files.length > 0) {
        return {
          path: submissionDir,
          files,
        };
      }
    }
  }

  // If no standard location found, try to find any class-0N directory
  // under my-work/ recursively
  const myWorkDir = path.join(repoPath, STUDENT_WORK_BASE);
  if (await dirExists(myWorkDir)) {
    const allFiles = await readCodeFiles(myWorkDir);
    if (allFiles.length > 0) {
      // Filter to files that seem related to this class
      const classNum = classId.replace('class-', '');
      const relevantFiles = allFiles.filter(f =>
        f.relativePath.includes(classId) || f.relativePath.includes(`class${classNum}`)
      );
      if (relevantFiles.length > 0) {
        return {
          path: myWorkDir,
          files: relevantFiles,
        };
      }
    }
  }

  return {
    path: null,
    files: [],
  };
}

/**
 * Formats file contents into a string suitable for the LLM prompt.
 * Truncates very large files to stay within token limits.
 */
export function formatFilesForPrompt(files, maxCharsPerFile = 8000) {
  if (!files || files.length === 0) {
    return '(No files found)';
  }

  return files
    .map(f => {
      let content = f.content;
      if (content.length > maxCharsPerFile) {
        content = content.slice(0, maxCharsPerFile) + '\n... [truncated]';
      }
      return `--- ${f.relativePath} ---\n${content}`;
    })
    .join('\n\n');
}

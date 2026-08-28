import Anthropic from '@anthropic-ai/sdk';
import { formatFilesForPrompt } from './courseService.js';

let client = null;

/**
 * Initializes the Anthropic client. Called once on startup.
 */
export function initGradingService() {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey || apiKey === 'your_api_key_here') {
    console.warn('⚠️  ANTHROPIC_API_KEY not set. Grading will not work until configured in .env');
    return false;
  }
  client = new Anthropic({ apiKey });
  console.log('✅ Anthropic client initialized');
  return true;
}

/**
 * Grades a student's submission using Claude as an LLM-as-Judge.
 *
 * Follows the methodology from GRADING-RUBRIC-TEMPLATE.md:
 * - Per-criterion verdicts (met / partial / not_met)
 * - Evidence quoted from the submission
 * - Anti-gaming: detects copying from golden solution
 * - Overall verdict: ready_to_move_on or needs_revision
 *
 * @param {Object} params
 * @param {Array} params.studentFiles - Student's code files
 * @param {Array} params.goldenSolutionFiles - Golden solution files
 * @param {string} params.gradingCriteria - GRADING.md content
 * @param {string} params.homework - homework.md content
 * @param {string} params.classId - e.g. "class-01"
 * @returns {Object} Structured grading result
 */
export async function gradeSubmission({
  studentFiles,
  goldenSolutionFiles,
  gradingCriteria,
  homework,
  classId,
}) {
  if (!client) {
    throw new Error('Anthropic client not initialized. Set ANTHROPIC_API_KEY in .env');
  }

  const studentCode = formatFilesForPrompt(studentFiles);
  const goldenCode = formatFilesForPrompt(goldenSolutionFiles);
  const classNumber = classId.replace('class-', '');

  const systemPrompt = `You are grading a student's submission for Class ${classNumber} of the Agent Engineering course against a rubric. Be an independent, skeptical reviewer — not the collaborator who helped build it.

Your job is to evaluate the QUALITATIVE aspects that automated tests cannot check. Passing pytest is necessary but not sufficient — you are checking whether the work demonstrates real understanding.

CRITICAL RULES:
- If the submission merely copies the gold reference's wording rather than demonstrating independent understanding, say so explicitly — that's a partial-met at best, regardless of test results.
- If the submission takes a legitimately different but equally valid approach from the gold reference, say so — don't penalize divergence from the reference when the underlying requirement is still satisfied.
- Don't grade against your own aesthetic preferences where the rubric is silent. If a criterion isn't in the rubric, it shouldn't affect the verdict.
- Quote or point to specific evidence in the submission for every judgment — don't just assert a verdict.`;

  const userMessage = `Here is the class-specific rubric (GRADING.md):

${gradingCriteria}

---

Here is the homework assignment (homework.md):

${homework}

---

Here is the gold reference solution:

${goldenCode}

---

Here is the student's submission:

${studentCode}

---

For each criterion in the rubric:
1. State whether it is **met**, **partially met**, or **not met**.
2. Quote or point to the specific evidence in the submission that supports your judgment.
3. If the submission merely copies the gold reference's wording rather than demonstrating independent understanding, say so explicitly.
4. If the submission takes a legitimately different but equally valid approach from the gold reference, say so.

Return your response as valid JSON (no markdown fencing, just raw JSON) with this exact structure:

{
  "criteria": [
    {
      "number": 1,
      "criterion": "Brief name of the criterion",
      "verdict": "met" | "partial" | "not_met",
      "evidence": "Quoted or referenced evidence from the submission",
      "reasoning": "Your explanation of the verdict"
    }
  ],
  "overallVerdict": "ready_to_move_on" | "needs_revision",
  "revisionPriority": "If needs_revision: the single most important thing to fix first. If ready_to_move_on: null",
  "summary": "A paragraph summarizing the overall assessment, including strengths and areas for growth",
  "verdictCounts": {
    "met": 0,
    "partial": 0,
    "not_met": 0
  }
}`;

  try {
    const response = await client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: userMessage,
        },
      ],
    });

    const responseText = response.content[0].text;

    // Parse the JSON response
    let result;
    try {
      // Try to extract JSON from the response (handle potential markdown fencing)
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        result = JSON.parse(jsonMatch[0]);
      } else {
        throw new Error('No JSON found in response');
      }
    } catch (parseErr) {
      console.error('Failed to parse Claude response as JSON:', parseErr.message);
      console.error('Raw response:', responseText.slice(0, 500));
      // Return a structured error result
      result = {
        criteria: [],
        overallVerdict: 'needs_revision',
        revisionPriority: 'Grading failed — could not parse AI response. Please retry.',
        summary: responseText.slice(0, 1000),
        verdictCounts: { met: 0, partial: 0, not_met: 0 },
        parseError: true,
      };
    }

    // Compute verdict counts if not provided
    if (!result.verdictCounts || result.parseError) {
      result.verdictCounts = {
        met: result.criteria.filter(c => c.verdict === 'met').length,
        partial: result.criteria.filter(c => c.verdict === 'partial').length,
        not_met: result.criteria.filter(c => c.verdict === 'not_met').length,
      };
    }

    return result;
  } catch (err) {
    console.error('Claude API error:', err.message);
    throw new Error(`Grading failed: ${err.message}`);
  }
}

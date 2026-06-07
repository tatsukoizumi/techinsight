export type RelevanceLevel = 1 | 2 | 3 | 4 | 5;

/**
 * Map a raw search score to a 1–5 level, relative to the top result in the
 * same result set. Absolute scores aren't comparable across search modes
 * (cosine similarity vs ts_rank), so we grade each result against the best match.
 */
export function relevanceLevel(score: number, maxScore: number): RelevanceLevel {
  if (maxScore <= 0) return 1;
  const ratio = score / maxScore;
  if (ratio >= 0.85) return 5;
  if (ratio >= 0.65) return 4;
  if (ratio >= 0.45) return 3;
  if (ratio >= 0.25) return 2;
  return 1;
}

import type { RelevanceLevel } from "@/lib/relevance";
import { cn } from "@/lib/utils";

const CONFIG: Record<RelevanceLevel, { label: string; color: string }> = {
  5: { label: "非常に高い", color: "bg-emerald-500" },
  4: { label: "高い", color: "bg-green-500" },
  3: { label: "ふつう", color: "bg-amber-500" },
  2: { label: "やや低い", color: "bg-orange-400" },
  1: { label: "低い", color: "bg-zinc-400" },
};

const SEGMENTS: RelevanceLevel[] = [1, 2, 3, 4, 5];

/** 5-level colored relevance indicator (replaces the opaque raw score). */
export function RelevanceMeter({ level }: { level: RelevanceLevel }) {
  const { label, color } = CONFIG[level];
  return (
    <span className="flex items-center gap-1" title={`関連度: ${label}`}>
      <span className="flex gap-0.5" aria-hidden>
        {SEGMENTS.map((i) => (
          <span key={i} className={cn("h-1.5 w-2.5 rounded-sm", i <= level ? color : "bg-muted")} />
        ))}
      </span>
      <span className="text-[10px] text-muted-foreground">関連度 {label}</span>
    </span>
  );
}

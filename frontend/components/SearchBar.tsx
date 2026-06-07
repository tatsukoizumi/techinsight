"use client";

import { CornerDownLeft, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SearchMode } from "@/lib/api/types";

const CATEGORIES = ["AI/ML", "Backend", "DevOps", "Frontend"];

type Props = {
  query: string;
  mode: SearchMode;
  category: string;
  /** True when the input has unsubmitted changes (shows the Enter hint). */
  pendingSearch: boolean;
  onQueryChange: (value: string) => void;
  onModeChange: (mode: SearchMode) => void;
  onCategoryChange: (category: string) => void;
  onSubmit: () => void;
};

export function SearchBar({
  query,
  mode,
  category,
  pendingSearch,
  onQueryChange,
  onModeChange,
  onCategoryChange,
  onSubmit,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9 pr-28"
            placeholder="キーワードや文章で検索…"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSubmit();
            }}
          />
          {pendingSearch ? (
            <span className="pointer-events-none absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-1 text-xs text-muted-foreground">
              <CornerDownLeft className="size-3.5" />
              Enter で検索
            </span>
          ) : null}
        </div>
        <div className="sm:w-44">
          <Select value={category} onChange={(e) => onCategoryChange(e.target.value)}>
            <option value="">すべてのカテゴリ</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <Tabs value={mode} onValueChange={(v) => onModeChange(v as SearchMode)}>
        <TabsList>
          <TabsTrigger value="keyword" title="入力した言葉が含まれる記事を探します">
            言葉で探す
            <span className="ml-1 text-[10px] opacity-60">キーワード</span>
          </TabsTrigger>
          <TabsTrigger value="semantic" title="言い回しが違っても意味の近い記事を探します">
            意味で探す
            <span className="ml-1 text-[10px] opacity-60">セマンティック</span>
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  );
}

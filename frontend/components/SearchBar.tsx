"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SearchMode } from "@/lib/api/types";

const CATEGORIES = ["AI/ML", "Backend", "DevOps", "Frontend"];

type Props = {
  query: string;
  mode: SearchMode;
  category: string;
  onQueryChange: (value: string) => void;
  onModeChange: (mode: SearchMode) => void;
  onCategoryChange: (category: string) => void;
};

export function SearchBar({
  query,
  mode,
  category,
  onQueryChange,
  onModeChange,
  onCategoryChange,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="キーワードや文章で検索…"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
          />
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
          <TabsTrigger value="hybrid" title="言葉の一致と意味の近さの両方から探します（おすすめ）">
            おすすめ
          </TabsTrigger>
          <TabsTrigger value="keyword" title="入力した言葉が含まれる記事を探します">
            言葉で探す
          </TabsTrigger>
          <TabsTrigger value="semantic" title="言い回しが違っても意味の近い記事を探します">
            意味で探す
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  );
}

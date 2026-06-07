"use client";

import { Info, Plus } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ArticleCard } from "@/components/ArticleCard";
import { ArticleForm } from "@/components/ArticleForm";
import { ArticleModal } from "@/components/ArticleModal";
import { Pagination } from "@/components/Pagination";
import { SearchBar } from "@/components/SearchBar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Article, SearchMode } from "@/lib/api/types";
import { useCreateArticle } from "@/lib/hooks/useArticleMutations";
import { useArticles } from "@/lib/hooks/useArticles";
import { useSearch } from "@/lib/hooks/useSearch";

const PAGE_SIZE = 12;

function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // The URL is the source of truth for the submitted query and mode, so the
  // search state survives reloads and is shareable / back-forward navigable.
  const submittedQuery = searchParams.get("q") ?? "";
  const mode: SearchMode = searchParams.get("mode") === "semantic" ? "semantic" : "keyword";

  const [query, setQuery] = useState(submittedQuery);
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Article | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  // Keep the input box in sync with the URL (e.g. on back/forward).
  useEffect(() => {
    setQuery(submittedQuery);
  }, [submittedQuery]);

  const searching = submittedQuery.trim().length > 0;
  const pendingSearch = query.trim() !== "" && query !== submittedQuery;

  const listQuery = useArticles({ page, size: PAGE_SIZE, category });
  const searchQuery = useSearch({ q: submittedQuery, mode, limit: 30, category }, searching);
  const createMutation = useCreateArticle();

  // Merge updates into the current query string. Falsy values drop the param
  // (mode=keyword is the default, so it stays out of the URL to keep it clean).
  function setParams(updates: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) params.set(key, value);
      else params.delete(key);
    }
    const qs = params.toString();
    router.replace(qs ? `/?${qs}` : "/", { scroll: false });
  }

  const articles = searching ? (searchQuery.data?.items ?? []) : (listQuery.data?.items ?? []);
  const isLoading = searching ? searchQuery.isLoading : listQuery.isLoading;
  const error = searching ? searchQuery.error : listQuery.error;

  // Top score in the current result set; relevance levels are graded against it.
  const maxScore = searching
    ? Math.max(0, ...(searchQuery.data?.items ?? []).map((item) => item.score))
    : undefined;

  function openArticle(article: Article) {
    setSelected(article);
    setModalOpen(true);
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">TechInsight</h1>
          <p className="text-sm text-muted-foreground">技術記事の AI 搭載ナレッジベース</p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="size-4" />
          新規作成
        </Button>
      </header>

      <div className="mb-6">
        <SearchBar
          query={query}
          mode={mode}
          category={category}
          pendingSearch={pendingSearch}
          onQueryChange={(value) => {
            setQuery(value);
            // Clearing the box returns to the full list immediately.
            if (value === "") setParams({ q: null });
          }}
          onModeChange={(value) => setParams({ mode: value === "semantic" ? "semantic" : null })}
          onCategoryChange={(value) => {
            setCategory(value);
            setPage(1);
          }}
          onSubmit={() => {
            setParams({ q: query.trim() || null });
            setPage(1);
          }}
        />
      </div>

      {searching && articles.length > 0 ? (
        <p className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Info className="size-3.5 shrink-0" />
          関連度が高い順に表示しています。色付きのバーは検索キーワードとの関連の強さ（5
          段階）の目安です。
        </p>
      ) : null}

      {error ? (
        <p className="py-12 text-center text-sm text-destructive">
          読み込みに失敗しました: {error.message}
        </p>
      ) : isLoading ? (
        <p className="py-12 text-center text-sm text-muted-foreground">読み込み中…</p>
      ) : articles.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          記事が見つかりませんでした。
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {articles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              maxScore={maxScore}
              onClick={() => openArticle(article)}
            />
          ))}
        </div>
      )}

      {!searching && listQuery.data ? (
        <div className="mt-8">
          <Pagination
            page={page}
            size={PAGE_SIZE}
            total={listQuery.data.total}
            onPageChange={setPage}
          />
        </div>
      ) : null}

      <ArticleModal article={selected} open={modalOpen} onOpenChange={setModalOpen} />

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>記事を新規作成</DialogTitle>
          </DialogHeader>
          <ArticleForm
            submitting={createMutation.isPending}
            error={createMutation.error?.message}
            onCancel={() => setCreating(false)}
            onSubmit={(input) =>
              createMutation.mutate(input, {
                onSuccess: () => setCreating(false),
              })
            }
          />
        </DialogContent>
      </Dialog>
    </main>
  );
}

export default function HomePage() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}

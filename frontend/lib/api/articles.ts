import { apiFetch } from "@/lib/api/client";
import type {
  Article,
  ArticleInput,
  ArticleList,
  SearchMode,
  SearchResponse,
} from "@/lib/api/types";

export type ListParams = {
  page?: number;
  size?: number;
  category?: string;
  sort?: "newest" | "oldest";
};

function toQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function listArticles(params: ListParams): Promise<ArticleList> {
  return apiFetch<ArticleList>(`/api/v1/articles${toQuery({ ...params })}`);
}

export function createArticle(input: ArticleInput): Promise<Article> {
  return apiFetch<Article>("/api/v1/articles", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateArticle(id: number, input: Partial<ArticleInput>): Promise<Article> {
  return apiFetch<Article>(`/api/v1/articles/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteArticle(id: number): Promise<void> {
  return apiFetch<void>(`/api/v1/articles/${id}`, { method: "DELETE" });
}

export type SearchParams = {
  q: string;
  mode: SearchMode;
  limit?: number;
  category?: string;
};

export function searchArticles(params: SearchParams): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`/api/v1/search${toQuery({ ...params })}`);
}

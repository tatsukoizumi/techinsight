import { useQuery } from "@tanstack/react-query";
import { type SearchParams, searchArticles } from "@/lib/api/articles";

export function useSearch(params: SearchParams, enabled: boolean) {
  return useQuery({
    queryKey: ["search", params],
    queryFn: () => searchArticles(params),
    enabled: enabled && params.q.trim().length > 0,
  });
}

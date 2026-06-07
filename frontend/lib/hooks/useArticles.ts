import { useQuery } from "@tanstack/react-query";
import { type ListParams, listArticles } from "@/lib/api/articles";

export function useArticles(params: ListParams) {
  return useQuery({
    queryKey: ["articles", params],
    queryFn: () => listArticles(params),
  });
}

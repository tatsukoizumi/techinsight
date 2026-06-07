import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createArticle, deleteArticle, updateArticle } from "@/lib/api/articles";
import type { ArticleInput } from "@/lib/api/types";

/** Invalidate every list/search query after a write so the UI reflects it. */
function useInvalidateArticles() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["articles"] });
    queryClient.invalidateQueries({ queryKey: ["search"] });
  };
}

export function useCreateArticle() {
  const invalidate = useInvalidateArticles();
  return useMutation({
    mutationFn: (input: ArticleInput) => createArticle(input),
    onSuccess: invalidate,
  });
}

export function useUpdateArticle() {
  const invalidate = useInvalidateArticles();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<ArticleInput> }) =>
      updateArticle(id, input),
    onSuccess: invalidate,
  });
}

export function useDeleteArticle() {
  const invalidate = useInvalidateArticles();
  return useMutation({
    mutationFn: (id: number) => deleteArticle(id),
    onSuccess: invalidate,
  });
}

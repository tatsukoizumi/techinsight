"use client";

import { useEffect, useState } from "react";
import { ArticleForm } from "@/components/ArticleForm";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Article } from "@/lib/api/types";
import { useDeleteArticle, useUpdateArticle } from "@/lib/hooks/useArticleMutations";

type Props = {
  article: Article | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function ArticleModal({ article, open, onOpenChange }: Props) {
  const [current, setCurrent] = useState<Article | null>(article);
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const updateMutation = useUpdateArticle();
  const deleteMutation = useDeleteArticle();

  // Reset view state whenever a different article is opened.
  useEffect(() => {
    setCurrent(article);
    setEditing(false);
    setConfirmingDelete(false);
  }, [article]);

  if (!current) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {editing ? (
          <>
            <DialogHeader>
              <DialogTitle>記事を編集</DialogTitle>
              <DialogDescription>変更を保存すると一覧と検索に即時反映されます。</DialogDescription>
            </DialogHeader>
            <ArticleForm
              initial={current}
              submitting={updateMutation.isPending}
              error={updateMutation.error?.message}
              onCancel={() => setEditing(false)}
              onSubmit={(input) =>
                updateMutation.mutate(
                  { id: current.id, input },
                  {
                    onSuccess: (updated) => {
                      setCurrent(updated);
                      setEditing(false);
                    },
                  },
                )
              }
            />
          </>
        ) : (
          <>
            <DialogHeader>
              <Badge variant="secondary" className="w-fit">
                {current.category}
              </Badge>
              <DialogTitle>{current.title}</DialogTitle>
              <DialogDescription>
                {current.author} ・ {new Date(current.published_at).toLocaleString("ja-JP")}
              </DialogDescription>
            </DialogHeader>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{current.content}</p>
            <DialogFooter>
              {confirmingDelete ? (
                <div className="flex w-full items-center justify-between gap-2">
                  <span className="text-sm text-destructive">本当に削除しますか？</span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setConfirmingDelete(false)}
                      disabled={deleteMutation.isPending}
                    >
                      キャンセル
                    </Button>
                    <Button
                      variant="destructive"
                      disabled={deleteMutation.isPending}
                      onClick={() =>
                        deleteMutation.mutate(current.id, {
                          onSuccess: () => onOpenChange(false),
                        })
                      }
                    >
                      {deleteMutation.isPending ? "削除中…" : "削除する"}
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <Button variant="destructive" onClick={() => setConfirmingDelete(true)}>
                    削除
                  </Button>
                  <Button onClick={() => setEditing(true)}>編集</Button>
                </>
              )}
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
};

export function Pagination({ page, size, total, onPageChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex items-center justify-center gap-4">
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        <ChevronLeft className="size-4" />
        前へ
      </Button>
      <span className="text-sm text-muted-foreground">
        {page} / {totalPages}（全 {total} 件）
      </span>
      <Button
        variant="outline"
        size="sm"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        次へ
        <ChevronRight className="size-4" />
      </Button>
    </div>
  );
}

"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Article, SearchResultItem } from "@/lib/api/types";

type Props = {
  article: Article | SearchResultItem;
  onClick: () => void;
};

function hasScore(article: Article | SearchResultItem): article is SearchResultItem {
  return "score" in article;
}

export function ArticleCard({ article, onClick }: Props) {
  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter") onClick();
      }}
      tabIndex={0}
      role="button"
    >
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <Badge variant="secondary">{article.category}</Badge>
          {hasScore(article) ? (
            <Badge variant="outline" title="検索キーワードとの関連度">
              関連度 {article.score.toFixed(3)}
            </Badge>
          ) : null}
        </div>
        <CardTitle className="line-clamp-2">{article.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="line-clamp-3 text-sm text-muted-foreground">{article.content}</p>
        <p className="mt-3 text-xs text-muted-foreground">
          {article.author} ・ {new Date(article.published_at).toLocaleDateString("ja-JP")}
        </p>
      </CardContent>
    </Card>
  );
}

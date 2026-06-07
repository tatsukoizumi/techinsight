export type Article = {
  id: number;
  title: string;
  content: string;
  author: string;
  category: string;
  published_at: string;
  created_at: string;
  updated_at: string;
};

export type ArticleInput = {
  title: string;
  content: string;
  author: string;
  category: string;
  published_at: string;
};

export type ArticleList = {
  items: Article[];
  total: number;
  page: number;
  size: number;
};

export type SearchMode = "keyword" | "semantic";

export type SearchResultItem = Article & { score: number };

export type SearchResponse = {
  items: SearchResultItem[];
  total: number;
  mode: SearchMode;
  query: string;
};

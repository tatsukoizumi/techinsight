// 一時的なスケルトン用 HTTP サーバ。Node 標準 http モジュールのみで動く。
// 次フェーズで Next.js を導入したらこのファイルごと削除し、Dockerfile の CMD を `pnpm dev` に切り替える。
import http from "node:http";

const PORT = Number(process.env.PORT ?? 3000);
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const html = `<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TechInsight (skeleton)</title>
    <style>
      :root { color-scheme: light dark; }
      body { font-family: system-ui, sans-serif; max-width: 720px; margin: 4rem auto; padding: 0 1rem; line-height: 1.6; }
      h1 { margin-bottom: 0; }
      .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; background: #eef; color: #224; font-size: 0.8rem; }
      code { background: rgba(127,127,127,0.15); padding: 1px 4px; border-radius: 3px; }
      ul { padding-left: 1.2rem; }
    </style>
  </head>
  <body>
    <h1>TechInsight</h1>
    <p><span class="badge">skeleton</span> Next.js は次フェーズで導入予定です。</p>
    <h2>確認用エンドポイント</h2>
    <ul>
      <li>Backend health: <a href="${API_BASE}/health"><code>${API_BASE}/health</code></a></li>
      <li>Backend OpenAPI: <a href="${API_BASE}/docs"><code>${API_BASE}/docs</code></a></li>
    </ul>
  </body>
</html>`;

http
  .createServer((req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ status: "ok", phase: "skeleton" }));
      return;
    }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(html);
  })
  .listen(PORT, "0.0.0.0");

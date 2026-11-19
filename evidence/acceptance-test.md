# INF601 Acceptance Test — Practice Hub MCP Server

Transcript of the acceptance test run through Claude Code using only the
`practice-hub` MCP tools. Each step shows the exact tool call and the result
the MCP server returned. Results are pretty-printed for readability; all
values are unchanged. Timestamps are as returned by the Hub.

## Summary

| Step | Tool call | Outcome |
|---|---|---|
| 1 | `list_posts(mine=true)` | Initial post IDs: **17, 16, 15** |
| 2 | `create_post(title="INF601 acceptance test", body="Created through Claude Code.", tags=["inf601", "mcp"])` | New post ID: **68** |
| 3 | `update_post(post_id=68, body="Updated through Claude Code.")` | Body changed; title and tags unchanged |
| 4 | `get_post(post_id=68)` | Saved body: **"Updated through Claude Code."** |

Post 68 was left in place for grading.

## Step 1 — List my posts

**Call:** `practice-hub` → `list_posts`

```json
{"mine": true}
```

**Result:**

```json
{
  "ok": true,
  "count": 3,
  "post_ids": [17, 16, 15],
  "data": [
    {
      "id": 17,
      "title": "Testing from VS Code",
      "body": "hello",
      "tags": ["test"],
      "author_id": 19,
      "author_name": "coyt mauch",
      "created_at": "2026-09-06T04:26:06.343448",
      "updated_at": "2026-09-06T04:26:06.343457",
      "attachments": []
    },
    {
      "id": 16,
      "title": "Testing from VS Code",
      "body": "hello",
      "tags": ["test"],
      "author_id": 19,
      "author_name": "coyt mauch",
      "created_at": "2026-09-06T04:01:18.741207",
      "updated_at": "2026-09-06T04:01:18.741217",
      "attachments": []
    },
    {
      "id": 15,
      "title": "Week 3 lab",
      "body": "My first created post.",
      "tags": [],
      "author_id": 19,
      "author_name": "coyt mauch",
      "created_at": "2026-09-06T03:43:54.186096",
      "updated_at": "2026-09-06T03:43:54.186105",
      "attachments": []
    }
  ]
}
```

## Step 2 — Create the test post

**Call:** `practice-hub` → `create_post`

```json
{
  "title": "INF601 acceptance test",
  "body": "Created through Claude Code.",
  "tags": ["inf601", "mcp"]
}
```

**Result:** the new post's ID is **68**.

```json
{
  "ok": true,
  "data": {
    "id": 68,
    "title": "INF601 acceptance test",
    "body": "Created through Claude Code.",
    "tags": ["inf601", "mcp"],
    "author_id": 19,
    "author_name": "coyt mauch",
    "created_at": "2026-11-19T02:50:08.962126",
    "updated_at": "2026-11-19T02:50:08.962135",
    "attachments": []
  }
}
```

## Step 3 — Update only the body of post 68

**Call:** `practice-hub` → `update_post`

```json
{
  "post_id": 68,
  "body": "Updated through Claude Code."
}
```

**Result:** the body changed; the title and tags kept their values, and
`updated_at` moved forward.

```json
{
  "ok": true,
  "data": {
    "id": 68,
    "title": "INF601 acceptance test",
    "body": "Updated through Claude Code.",
    "tags": ["inf601", "mcp"],
    "author_id": 19,
    "author_name": "coyt mauch",
    "created_at": "2026-11-19T02:50:08.962126",
    "updated_at": "2026-11-19T02:50:17.890341",
    "attachments": []
  }
}
```

## Step 4 — Confirm the saved body

**Call:** `practice-hub` → `get_post`

```json
{"post_id": 68}
```

**Result:** the Hub returns the updated body, confirming the change was saved.

```json
{
  "ok": true,
  "data": {
    "id": 68,
    "title": "INF601 acceptance test",
    "body": "Updated through Claude Code.",
    "tags": ["inf601", "mcp"],
    "author_id": 19,
    "author_name": "coyt mauch",
    "created_at": "2026-11-19T02:50:08.962126",
    "updated_at": "2026-11-19T02:50:17.890341",
    "attachments": []
  }
}
```

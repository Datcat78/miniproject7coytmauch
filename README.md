# Practice Hub MCP Server

INF601 Mini Project 7.

## Purpose

This project is a Model Context Protocol (MCP) server that lets Claude Code
read and manage posts on the Practice Hub (`https://practice.fhsucyber.com`).
It runs on your own computer over stdio and gives Claude five tools: list,
get, create, update and delete posts.

Every tool goes through one shared helper, `practice_hub_request`. It reuses
the working `PracticeHubClient` from Mini Project 1 and gives every request a
10-second timeout. It turns problems (missing configuration, HTTP 401, 403,
404 and 422 errors, server errors, timeouts and connection failures) into
clear error results. The API token is never printed or returned.

## Project files

| File | Purpose |
|---|---|
| [`server.py`](server.py) | FastMCP server named `practice-hub` that defines the five tools |
| [`Practice_Hub_Client.py`](Practice_Hub_Client.py) | API client from Mini Project 1. It adds `/api/v1` to the URL and sends the `Authorization: Bearer` header |
| [`evidence/acceptance-test.md`](evidence/acceptance-test.md) | Transcript of the acceptance test |

## Prerequisites

- Windows 10 or 11 with Windows PowerShell
- Python 3.13, run through the `py` launcher (this project was built with 3.13.15)
- The Claude Code CLI (`claude --version` should print a version)
- A Practice Hub account and your personal Practice Hub API token

## Setup (Windows PowerShell)

### 1. Open the project folder

```powershell
cd path\to\miniproject7coytmauch
```

Run every command below from this folder.

### 2. Create and activate a virtual environment

```powershell
py -3.13 -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
```

`Set-ExecutionPolicy -Scope Process` lets PowerShell run the activation script.
It only affects the current window.

### 3. Install the dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install "mcp<2" requests
.\.venv\Scripts\python.exe -c "from mcp.server.fastmcp import FastMCP; import requests; print('Imports OK')"
```

The second command should print `Imports OK`. `mcp` must stay below 2.0
because version 2 removed `mcp.server.fastmcp`, which `server.py` imports. The
project was built and tested with `mcp` 1.30.0 and `requests` 2.34.2.

### 4. Set `PRACTICE_API_URL` and `PRACTICE_API_TOKEN`

The server reads two environment variables when it starts:

| Variable | Value |
|---|---|
| `PRACTICE_API_URL` | The Hub's site root: `https://practice.fhsucyber.com` |
| `PRACTICE_API_TOKEN` | Your personal Practice Hub API token |

**Which part of the Hub URL to enter:** only the scheme and the host name,
`https://practice.fhsucyber.com`. If your browser shows a longer address, such
as `https://practice.fhsucyber.com/docs`, drop everything from the `/` after
`.com` onward.

- Don't add `/api/v1`. `PracticeHubClient` adds it itself, so including it
  would send requests to `/api/v1/api/v1/posts`.
- Keep the `https://`. The server rejects a URL that doesn't start with
  `http://` or `https://`.
- A trailing slash doesn't matter, because the client removes it.

Set both variables in the PowerShell window you will start Claude Code from:

```powershell
$env:PRACTICE_API_URL = "https://practice.fhsucyber.com"

# Copy your API token from Practice Hub first, then run:
$env:PRACTICE_API_TOKEN = (Get-Clipboard).Trim()
$env:PRACTICE_API_TOKEN.Length   # should be your token's full length, not 1
```

- Use only the token itself. Don't put `Bearer ` in front, because the client
  adds it.
- Reading the clipboard with `Get-Clipboard` avoids a failed Ctrl+V paste. A
  failed paste once stored one invisible character as the token, which caused
  HTTP 400 errors (see [AI Usage](#ai-usage)).
- `$env:` variables last only as long as the PowerShell window. Set them again
  in every new window before you start `claude`.
- Never save the token in a file inside this repository.

### 5. Register the server with Claude Code

In the same window, from the project folder, run:

```powershell
$pythonPath = (Resolve-Path ".\.venv\Scripts\python.exe").Path
$serverPath = (Resolve-Path ".\server.py").Path
claude mcp add --scope local --env 'PRACTICE_API_URL=${PRACTICE_API_URL}' --env 'PRACTICE_API_TOKEN=${PRACTICE_API_TOKEN}' --transport stdio practice-hub -- "$pythonPath" "$serverPath"
```

What each part does:

- **The two `Resolve-Path` lines** turn the relative paths into full paths.
  That way Claude Code can start the virtual environment's Python and
  `server.py` from any folder.
- **`--scope local`** registers the server for this project only. The
  registration is saved in your own Claude Code config (`~/.claude.json`), not
  in the repository.
- **`--env '...=${...}'`** passes literal environment variable references. The
  single quotes stop PowerShell from expanding `${PRACTICE_API_URL}` and
  `${PRACTICE_API_TOKEN}` itself. Claude Code saves the references, not the
  values, and fills them in from its own environment each time it starts the
  server. That's why both variables must be set before you run `claude`, and
  why the token is never written to the config file.
- **`--transport stdio`** makes Claude Code start the server as a child process
  and talk to it over standard input and output.
- **Everything after `--`** is the command that starts the server.

Check what was saved:

```powershell
claude mcp get practice-hub
```

The Environment section should show `PRACTICE_API_TOKEN=${PRACTICE_API_TOKEN}`,
not your token. To change the registration later, run
`claude mcp remove practice-hub -s local`, then run the `add` command again.

## Verify the connection with `/mcp`

1. Start Claude Code from the project folder, in the same window where you set
   both variables:

   ```powershell
   claude
   ```

2. Type `/mcp`.
3. `practice-hub` should be listed as connected. Select it to see its tools.
   There should be five.
4. If you changed a variable after Claude Code started, select `practice-hub`
   and choose **Reconnect**, or restart Claude Code. The server reads the
   variables only when it starts. Do the same if the server shows as failed.
5. Ask Claude: *Use the practice-hub list_posts tool with mine=true.* A working
   setup returns `"ok": true` and your post IDs.

`claude mcp list`, run in PowerShell, also health-checks the server and should
show `practice-hub` as `✔ Connected`. That check only proves the server starts.
Step 5 is what proves the URL and token work.

## Tools

| Tool | Arguments | What it does | Hub request |
|---|---|---|---|
| `list_posts` | `mine: bool = False` | Lists posts. `mine=True` returns only posts owned by the token's user. The result includes `count` and `post_ids`. | `GET /api/v1/posts`, or `GET /api/v1/posts?mine=true` |
| `get_post` | `post_id: int` | Gets one post with its full body. | `GET /api/v1/posts/{post_id}` |
| `create_post` | `title: str`, `body: str = ""`, `tags: list[str] \| None = None` | Creates a post owned by you. The new post's ID is `data.id`. | `POST /api/v1/posts` |
| `update_post` | `post_id: int`, `title: str \| None = None`, `body: str \| None = None`, `tags: list[str] \| None = None` | Changes only the fields you pass. The others keep their values. `tags` replaces the whole list, and `[]` clears it. | `PATCH /api/v1/posts/{post_id}` |
| `delete_post` | `post_id: int` | Permanently deletes a post you own. The Hub's empty 204 response becomes a confirmation message. | `DELETE /api/v1/posts/{post_id}` |

Every tool returns `{"ok": true, "data": ...}` on success, or
`{"ok": false, "status": <HTTP status or null>, "error": "<message>"}` on
failure. The error messages say what to check:

- **401:** the token is wrong or expired.
- **403:** the post isn't yours. The Hub decides who owns a post.
- **404:** no post has that ID, or `PRACTICE_API_URL` includes `/api/v1`.
- **422:** the Hub rejected the data.
- **Server errors, timeouts, connection failures and missing variables** each
  get their own message too.

## Acceptance test

The acceptance test runs a full read → create → modify → verify cycle, using
only the `practice-hub` MCP tools inside Claude Code:

1. **Read:** `list_posts(mine=true)` shows my existing post IDs.
2. **Create:** `create_post(title="INF601 acceptance test", body="Created through Claude Code.", tags=["inf601", "mcp"])` returns the new post's ID.
3. **Modify:** `update_post` on that same ID changes only the body, to
   `"Updated through Claude Code."`
4. **Verify:** `get_post` on the same ID shows the saved body.

| Step | Result |
|---|---|
| Read | Starting post IDs: 17, 16, 15 |
| Create | New post ID: 68 |
| Modify | The body changed. The title and tags kept their values, and `updated_at` moved forward |
| Verify | `get_post(68)` returned the body `"Updated through Claude Code."` |

Post 68 was left on the Hub for grading. Every tool call and the JSON the
server returned are in
[evidence/acceptance-test.md](evidence/acceptance-test.md).

## AI Usage

I used Claude Code, Anthropic's AI coding assistant, in PowerShell throughout
this project. I gave it step-by-step prompts for each part of the project. I
created the virtual environment, ran the `py_compile` checks and made every
Git commit myself.

### What Claude did

- **Wrote the server code.** Claude wrote `server.py`: the FastMCP setup, the
  shared `practice_hub_request` helper and its error messages, and the five
  tools. Each tool's docstring tells Claude when to use it. The tools reuse my
  `PracticeHubClient` from Mini Project 1 instead of new HTTP code.
- **Checked the API.** Claude read the Hub's public OpenAPI schema, which
  needs no token, to confirm how the `mine` filter works and which fields
  create and update accept.
- **Tested before going live.** Claude tested the tools over a real stdio MCP
  connection against a local fake Hub. It then wrote Python mock tests for a
  403 on update, a 404 on get and an empty 204 on delete. None of these tests
  contacted the real Hub.
- **Ran the live tests.** Claude tested create, update and delete on a
  temporary post, then ran the acceptance test.
- **Wrote the documentation.** Claude wrote `evidence/acceptance-test.md` from
  the real tool results. It wrote this README from the code, my PowerShell
  history and the Claude Code session transcripts.

### Troubleshooting

1. **`mcp.server.fastmcp` was missing.** Claude installed `mcp` and `requests`
   in the virtual environment. The newest `mcp` (2.x) no longer includes
   `mcp.server.fastmcp`, so Claude pinned it to `mcp<2`, which installed
   1.30.0.

2. **The first run of the mock tests failed.** All three tests failed with
   "live network call attempted". The test's safety net blocked every socket
   connection, including the local `127.0.0.1` connection that Python's
   asyncio opens on Windows. Claude changed the safety net to allow only local
   loopback addresses. All three checks then passed, and `server.py` didn't
   need any change.

3. **The tools weren't available, then reported "Missing configuration".**
   Right after I registered the server, its tools didn't appear in the Claude
   Code session that was already open. Claude Code only loads MCP tools when a
   session starts. In the next session, `list_posts` returned
   `Missing configuration: set PRACTICE_API_URL and PRACTICE_API_TOKEN`. The
   registration had an empty environment, and neither variable was set in
   Windows.
   **Fix:** set both variables before starting Claude Code, then restart it or
   reconnect from `/mcp`.

4. **Every call failed with HTTP 400 Bad Request.** `list_posts` failed with a
   400 for both `mine=true` and `mine=false`, so the filter wasn't the cause.
   At first Claude couldn't inspect the MCP config, because Claude Code's
   permission check blocked reading a file that contains the token. In the
   next session, Claude checked the variable without printing it. It found
   that `PRACTICE_API_TOKEN` was a single invisible character, `0x16`. That's
   the Ctrl+V keystroke, stored when the paste didn't go through. The site's
   front-end web server rejects a header that contains a control character
   with a plain 400, before the API sees the request. That's why it wasn't a
   401. Claude reproduced this with my own `PracticeHubClient`: a fake token
   got a 401, and a token containing a control character got a 400.
   **Fix:** set the token from the clipboard with
   `$env:PRACTICE_API_TOKEN = (Get-Clipboard).Trim()`, then check its length.
   I gave Claude the token so it could confirm it worked with a read-only
   request, which returned my posts 17, 16 and 15. Claude then re-registered
   `practice-hub` with the URL and token saved directly in my local Claude
   Code config (`~/.claude.json`, outside the repository). After I chose
   **Reconnect** in `/mcp`, `list_posts` and `get_post` worked. Claude
   recommended making a new token when the project is done, since this one
   had been shared in the chat.

5. **Checking create, update and delete on live data.** Before the acceptance
   test, Claude created a temporary post (ID 68). It changed only the title,
   cleared the tags and deleted the post. It then confirmed that `get_post(68)`
   returned 404 and that my original three posts hadn't changed. Claude Code's
   permission check blocked one extra call, an `update_post` with no fields
   aimed at my real post 15, so it never ran. The 403 for editing someone
   else's post was tested only with mocks. In the acceptance test, the Hub
   assigned ID 68 again to the new post.

6. **Keeping the token out of the config.** While writing this README, Claude
   tested a throwaway server, then removed it. The test confirmed that Claude
   Code fills in `${...}` references in a local `--env` value when it starts
   the server. That's why the registration command above can use
   `${PRACTICE_API_TOKEN}` instead of the token itself.

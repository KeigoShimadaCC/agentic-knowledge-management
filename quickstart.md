# KnowledgeOS Quickstart

For non-engineers. Keep it simple: run two commands, open the app, start using it.

## Before You Start

- Install Docker Desktop and make sure it is running.
- Open Terminal and go to this project folder.

## Start the App

Run these commands:

```bash
bash scripts/setup.sh
docker compose -f infra/docker-compose.yml up -d
```

Now open:

- `http://localhost:3000`

The first startup can take a few minutes.

## If Something Goes Wrong

**"address already in use" (port 8001)**  
Something else is already using port 8001 (often a copy of the API started outside Docker). Stop that program, then run `docker compose -f infra/docker-compose.yml up -d` again.

**Docker mentions `YOUR_USERNAME` or "no such file or directory" for the library**  
`infra/.env` still has the example library path. Run `bash scripts/setup.sh` again — it fixes a leftover `YOUR_USERNAME` path when it finds one. Then recreate the library volume once and start the stack:

```bash
docker compose -f infra/docker-compose.yml down
docker volume rm infra_library-data
docker compose -f infra/docker-compose.yml up -d
```

Only do this if you hit that mount error. It removes Docker’s **library bind volume** so it can be recreated with the correct path; your files under `~/KnowledgeOS/library` on the Mac are separate.

**The site shows "Internal Server Error"**  
First check you are really using the **Docker** web app, not a separate dev server:

1. Run `docker ps` — you should see a container named **`kos-web`** using port **3000**.
2. Open **`http://127.0.0.1:3000/login`** (sign-in page). If that loads, use **Register** or **Sign in** from there; the home URL `/` only redirects and can look confusing in the browser.
3. If you use **`pnpm dev`** for the frontend on your Mac **while** the API stays in Docker, create `apps/web/.env.local` from `apps/web/.env.local.example` so the app talks to port **8001**.

If it still fails only inside Docker, reset the web app’s dependency volume and rebuild (safe; only clears cached `node_modules` inside Docker):

```bash
docker compose -f infra/docker-compose.yml rm -sf web
docker volume rm infra_kos-web-node-modules
docker compose -f infra/docker-compose.yml up -d --build web
```

`rm -sf web` stops and removes the `web` container so the volume is no longer in use (`stop` alone is not enough).

**Still stuck**  
Share the last lines of:  
`docker compose -f infra/docker-compose.yml logs web --tail 50`  
and  
`docker compose -f infra/docker-compose.yml logs api --tail 50`.

## What To Do In The App

- Create your account and sign in.
- Create a page and write notes.
- Upload files (PDFs, images, etc.).
- Use search to find your notes and files quickly.
- Open items and connect related knowledge.

## Stop the App

When you are done:

```bash
docker compose -f infra/docker-compose.yml down
```

## Start Again Later

Next time, you only need:

```bash
docker compose -f infra/docker-compose.yml up -d
```

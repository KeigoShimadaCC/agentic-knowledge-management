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

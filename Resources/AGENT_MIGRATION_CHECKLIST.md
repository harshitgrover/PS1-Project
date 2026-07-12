# Agent Migration Checklist — Reusable Process

This is exactly what was done for Dxf_reader, generalized so it can be repeated for
`dxf_generator`, `web_crawler`, or any other agent/tool getting prepped for merge into `main`.

## A. Contract compliance (agent_owner_checklist.md)

1. Confirm `POST /run`, `GET /health`, `GET /metrics` all exist and match the exact paths
   (not `/api/health` or similar variants).
2. Confirm the 3 required metrics are defined module-level: `REQUEST_COUNT`,
   `INFERENCE_LATENCY`, `MODEL_ERROR_COUNT` — and that `/run` is wrapped with
   `INFERENCE_LATENCY.time()` and increments the counters on both success and error.
3. FastAPI agents: `Instrumentator().instrument(app).expose(app)` right after `app = FastAPI(...)`.
   Flask agents: manual `/metrics` route using `generate_latest()`.

## B. Code correctness

4. Cross-check every `import` in the code against `requirements.txt` — missing packages
   fail silently at runtime, not at review time (this is exactly what was wrong with
   Dxf_reader's `openai` import).
5. Any outbound call to an external API/LLM (GitHub Models, OpenAI, etc.) must set an
   explicit `timeout=` — the default SDK timeout (often 600s) can hang a worker and
   starve the whole pod under low worker counts.
6. No hardcoded `localhost`/`127.0.0.1` calls to other agents — must come from env vars.
7. No writing state/output files to the app root — must use `/tmp` or a per-request temp dir.

## C. Secrets

8. Real `.env` lives *inside* the agent's own folder (next to its entrypoint file), never
   at repo root — `load_dotenv()` searches upward, but colocating avoids ambiguity and
   matches the Docker build context.
9. Add an `.env.example` in the same folder — variable names only, no real values.
10. Confirm `.env`, `.env.local`, `.env.*.local` are covered by the root `.gitignore`
    (already done repo-wide — just confirm you don't have a stray tracked `.env`
    like the one found for Dxf_reader).

## D. Docker

11. Write/confirm a `Dockerfile` in the agent's folder: correct base image, install
    `requirements.txt`, run via a production server (`gunicorn` for Flask, `uvicorn`
    for FastAPI) — never the framework's dev server.
12. Actually build it: `docker build -t <agent>-test .`
13. Actually run it: `docker run -d -p <port>:<port> --env-file <agent>/.env <agent>-test`
14. Hit it for real — don't just assume:
    ```bash
    curl http://localhost:<port>/health
    curl http://localhost:<port>/metrics | head -5
    curl -X POST http://localhost:<port>/run -H "Content-Type: application/json" -d '{}'
    ```
15. If the agent calls an external API (LLM, etc.), exercise that path for real from
    *inside* the container (e.g. via a CLI test script), not just from your host — confirms
    network egress and the token both work in the containerized environment.
16. `docker rm -f`/`docker rmi` the test container/image when done — don't leave it running.

## E. Repo placement

17. Check the naming/location convention already used in `main` (`src/tools/<name>/` for
    standalone utilities like `z3_verifier`, `src/agents/<name>/` for full agents like
    `civil`/`site_plan`) — lowercase, underscores, matching whatever sibling folders exist.
18. If the folder needs to move, use `git mv` (not delete+recreate) so history/blame is
    preserved, then commit that move as its own commit, separate from code changes.

## F. Committing & merging

19. Stage and commit in small, scoped commits — don't mix unrelated folders/root files
    into an agent's commit unless they exist specifically to support that agent.
20. Before merging into `main`, dry-run it locally without touching your real branch:
    ```bash
    git branch -f _merge_test <your-branch>
    git checkout _merge_test
    git merge origin/main --no-commit --no-ff
    # inspect git status for conflicts, then:
    git merge --abort
    git checkout <your-branch>
    git branch -D _merge_test
    ```
21. Push your branch, open/update the PR, merge once conflict-free.

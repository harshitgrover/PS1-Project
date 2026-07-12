# SummerHouse Mint: Deployment Guidelines and Best Practices

To ensure a smooth transition from local development to our Kubernetes production environment, all developers must adhere to the following guidelines. These practices are necessary to prevent deployment failures, data corruption, and runtime errors.

---

## 1. Dependency Management
When one agent requires a Python library, other agents will not automatically have access to it in a containerized environment.
* **Dedicated `requirements.txt`:** Every agent must maintain its own `requirements.txt` file in its root directory.
* **Explicit Inclusions:** Ensure all libraries imported in your Python code are explicitly listed in your `requirements.txt`. Do not rely on libraries being installed globally or by other agents.

## 2. Networking and APIs
In our Kubernetes cluster, every agent runs in an isolated container.
* **Avoid Hardcoding `localhost`:** Do not use `http://localhost` or `127.0.0.1` for API calls between different agents. In a containerized setup, `localhost` only refers to the agent's own container.
* **Use Environment Variables:** All external API endpoints and base URLs must be fetched using environment variables (e.g., `os.environ.get("AGENT_MANAGER_URL")`). The deployment system will inject the correct internal network addresses automatically.

## 3. State Management and File I/O
Production containers are ephemeral and handle multiple requests concurrently.
* **Do Not Write State to Local Files:** Avoid saving temporary outputs or shared state (e.g., `.json` data files) directly to the application's root directory (`/app`). If multiple API requests occur simultaneously, they will overwrite each other's files and cause data corruption.
* **Use Designated Directories or In-Memory Stores:** If you must write temporary files, write them to `/tmp/`. For caching or state that must be shared, utilize a database or Redis instead of the local filesystem.

## 4. Environment Variables and Secrets
* **Secure API Keys:** Do not hardcode sensitive information such as Supabase credentials or LLM API keys directly into the source code.
* **Provide Configuration Templates:** Maintain an updated `.env.example` file in the repository. This provides a clear list of all required environment variables needed for the deployment team to configure the servers.
* **Handle Missing Variables:** Use `os.environ.get("KEY", None)` and include clear error logging if a critical environment variable is missing during application startup.

## 5. Docker Build Standards
* **System-Level Dependencies:** If your agent requires heavy libraries that rely on C-bindings (such as mathematical solvers or spatial libraries), ensure the Dockerfile includes the commands to install the necessary OS-level packages (e.g., `apt-get install -y build-essential`).
* **Production Servers:** Ensure the Dockerfile `CMD` uses a production-ready web server like `gunicorn` rather than the default development server.

## 6. Git Workflow and Repository Hygiene
* **Exclude Generated Artifacts:** Ensure your `.gitignore` is configured to prevent committing generated files such as `.html` visualizations, `.json` cache files, and `.dxf` CAD exports. Committing these files leads to repository bloat and merge conflicts.
* **Exclude Python Caches:** Ensure all `__pycache__` directories are ignored.
* **Verify Before Committing:** Ensure all source code, updated requirements, and Dockerfiles are thoroughly tested locally before merging into the main repository branch.

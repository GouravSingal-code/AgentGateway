# AgentGateway

An MCP-compatible integration gateway for LLM agents — with built-in evaluation, observability, multi-tenant routing, and tool calling across real SaaS integrations.

> Built as a reference implementation of agent infrastructure: what Composio, LangChain, and similar platforms solve at scale, distilled into a single runnable project.

---

## What It Does

AgentGateway is a backend platform that sits between your LLM agent and the outside world. It solves three problems:

1. **Tool calling at scale** — Agents call real APIs (GitHub, Notion, Gmail, Linear) through a unified function-schema interface, without hardcoding auth or API logic into the agent itself.
2. **Evaluation** — Every agent run is scored on accuracy, latency, and token cost. The eval harness drives model routing decisions automatically.
3. **Multi-tenancy & governance** — Each user gets an isolated API key, per-tenant audit logs, rate limiting, and OAuth2-scoped access to integrations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client                           │
│              (LLM App / Agent Orchestrator)             │
└────────────────────────┬────────────────────────────────┘
                         │  REST / MCP Protocol
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   API Gateway Layer                     │
│         FastAPI  |  Auth Middleware  |  Rate Limiter    │
│              Per-tenant API Key validation              │
└──────┬──────────────────┬────────────────────┬──────────┘
       │                  │                    │
       ▼                  ▼                    ▼
┌─────────────┐  ┌────────────────┐  ┌────────────────────┐
│  Agent      │  │  Tool Registry │  │  Eval Harness      │
│  Executor   │  │  (MCP Server)  │  │                    │
│             │  │                │  │  - Test runner     │
│  LangGraph  │  │  GitHub        │  │  - Accuracy scorer │
│  multi-step │  │  Notion        │  │  - Cost tracker    │
│  workflows  │  │  Gmail         │  │  - Model router    │
│             │  │  Linear        │  │                    │
└──────┬──────┘  └───────┬────────┘  └────────┬───────────┘
       │                 │                    │
       └────────┬────────┘                    │
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────┐
│      Observability        │   │     Storage Layer        │
│                           │   │                          │
│  - Per-run token cost     │   │  PostgreSQL              │
│  - Latency traces         │   │  - Audit logs            │
│  - Tool call sequences    │   │  - Eval results          │
│  - Structured JSON logs   │   │  - Tenant config         │
│                           │   │                          │
│  Redis (prompt cache)     │   │  Redis                   │
│  - Cache hit/miss ratio   │   │  - Prompt response cache │
└───────────────────────────┘   └─────────────────────────┘
```

---

## Core Features

### 1. MCP-Compatible Tool Registry

Each integration is exposed as an MCP tool with a structured JSON schema. The agent calls tools by name — AgentGateway handles auth, rate limiting, and error handling transparently.

```python
# Example tool schema (GitHub)
{
  "name": "github_create_issue",
  "description": "Create a GitHub issue in a repository",
  "parameters": {
    "type": "object",
    "properties": {
      "repo": { "type": "string" },
      "title": { "type": "string" },
      "body": { "type": "string" }
    },
    "required": ["repo", "title"]
  }
}
```

Supported integrations:
| Integration | Supported Actions |
|---|---|
| GitHub | create/list issues, PR status, file reads |
| Notion | read/write pages, search workspace |
| Gmail | send email, read inbox, search |
| Linear | create issues, update status, list projects |

### 2. LangGraph Multi-Step Agent

The agent executor uses LangGraph's state machine model to run multi-step workflows with conditional branching, retries, and parallel tool execution.

```
START
  │
  ▼
[Plan Step]──────────────────────────┐
  │                                  │
  ▼                                  │
[Execute Tools (parallel)]           │
  │                                  │
  ├─ GitHub Tool ──┐                 │
  ├─ Notion Tool ──┤──► [Merge]      │
  └─ Gmail Tool ───┘      │          │
                          ▼          │
                    [Evaluate]       │
                          │          │
                    [Need more?]─────┘
                          │
                         END
```

### 3. LLM Evaluation Framework

Every agent run is automatically evaluated and stored. The eval harness supports:

- **Accuracy scoring** — compare agent output against expected output using semantic similarity + exact match
- **Cost tracking** — log input/output token counts per model, compute USD cost using live pricing
- **Latency profiling** — measure end-to-end time, time-to-first-token, tool execution time separately
- **Model routing** — after N eval runs, automatically promote the cheaper model if quality stays above threshold

```
Eval Run Result:
{
  "run_id": "uuid",
  "model": "claude-3-5-haiku",
  "accuracy_score": 0.91,
  "total_tokens": 1842,
  "cost_usd": 0.0018,
  "latency_ms": 1240,
  "tool_calls": ["github_list_issues", "notion_read_page"],
  "routed_from": "claude-sonnet-4-6"
}
```

### 4. Multi-Tenant Architecture

Each tenant gets:
- Isolated API key with scoped permissions
- Per-tenant OAuth2 credentials for each integration (no credential sharing)
- Separate audit log partition in PostgreSQL
- Configurable rate limits (requests/min, tokens/day)

```
Tenant A ──► API Key A ──► GitHub OAuth (Tenant A's token)
                       ──► Notion OAuth (Tenant A's token)

Tenant B ──► API Key B ──► GitHub OAuth (Tenant B's token)
                       ──► Linear OAuth (Tenant B's token)
```

### 5. Audit Logging & Governance

Every tool call is logged with full context:

```sql
CREATE TABLE audit_logs (
  id          UUID PRIMARY KEY,
  tenant_id   UUID NOT NULL,
  run_id      UUID NOT NULL,
  tool_name   VARCHAR(100),
  input_args  JSONB,
  output      JSONB,
  status      VARCHAR(20),  -- success | error | timeout
  latency_ms  INT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

Audit logs are retained for 90 days by default (configurable per tenant).

### 6. Prompt Caching (Redis)

Identical prompt prefixes are cached in Redis with a configurable TTL. For workflows that re-use system prompts or static context, this cuts token spend significantly.

```
Cache Key: sha256(model + system_prompt + first_N_user_tokens)
TTL: 1 hour (configurable)
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API Server | FastAPI | Async-native, OpenAPI docs auto-generated |
| Agent Runtime | LangGraph | Stateful multi-step workflows with retries |
| LLM | Anthropic / OpenAI (configurable) | Model-agnostic via adapter |
| Database | PostgreSQL | Audit logs, eval results, tenant config |
| Cache | Redis | Prompt caching, rate limit counters |
| Auth | OAuth2 + API Keys | Per-tenant integration auth |
| Containers | Docker + Docker Compose | Single-command local setup |
| Protocol | MCP (Model Context Protocol) | Standard tool interface |

---

## Project Structure

```
AgentGateway/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── agent.py        # POST /run — execute agent
│   │   │   ├── eval.py         # POST /eval — run eval suite
│   │   │   ├── tools.py        # GET /tools — list available tools
│   │   │   └── tenants.py      # tenant management
│   │   └── middleware/
│   │       ├── auth.py         # API key validation
│   │       └── rate_limit.py   # per-tenant rate limiting
│   ├── agent/
│   │   ├── executor.py         # LangGraph agent definition
│   │   ├── router.py           # model routing logic
│   │   └── prompts.py          # prompt templates
│   ├── tools/
│   │   ├── registry.py         # tool registration & MCP schema
│   │   ├── github.py           # GitHub integration
│   │   ├── notion.py           # Notion integration
│   │   ├── gmail.py            # Gmail integration
│   │   └── linear.py           # Linear integration
│   ├── eval/
│   │   ├── harness.py          # test runner
│   │   ├── scorer.py           # accuracy scoring
│   │   └── test_cases/         # YAML test case definitions
│   ├── observability/
│   │   ├── tracer.py           # per-run logging
│   │   └── cost.py             # token cost computation
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models
│   │   └── migrations/         # Alembic migrations
│   └── cache/
│       └── prompt_cache.py     # Redis caching layer
├── tests/
│   ├── unit/
│   └── integration/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- API keys for: Anthropic (or OpenAI), GitHub, Notion, Gmail OAuth app, Linear

### 1. Clone and configure

```bash
git clone https://github.com/GouravSingal-code/AgentGateway
cd AgentGateway
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Start all services

```bash
docker-compose up -d
```

This starts:
- FastAPI server on `localhost:8000`
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

### 3. Run database migrations

```bash
docker-compose exec app alembic upgrade head
```

### 4. Create a tenant and get an API key

```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "my-tenant"}'

# Response: { "api_key": "agw_xxxxxxxxxxxx" }
```

### 5. Run your first agent

```bash
curl -X POST http://localhost:8000/run \
  -H "X-API-Key: agw_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List my open GitHub issues and create a Notion page summarizing them",
    "tools": ["github_list_issues", "notion_create_page"],
    "model": "claude-sonnet-4-6"
  }'
```

---

## API Reference

### `POST /run`
Execute an agent run.

```json
Request:
{
  "prompt": "string",
  "tools": ["tool_name", ...],
  "model": "claude-sonnet-4-6 | claude-haiku-4-5 | gpt-4o",
  "max_steps": 10
}

Response:
{
  "run_id": "uuid",
  "output": "string",
  "tool_calls": [...],
  "tokens_used": { "input": 842, "output": 312 },
  "cost_usd": 0.0024,
  "latency_ms": 1840
}
```

### `POST /eval`
Run the evaluation harness against a test suite.

```json
Request:
{
  "suite": "github_workflows",
  "models": ["claude-sonnet-4-6", "claude-haiku-4-5"],
  "runs_per_case": 3
}

Response:
{
  "results": [
    {
      "model": "claude-haiku-4-5",
      "avg_accuracy": 0.88,
      "avg_cost_usd": 0.0009,
      "avg_latency_ms": 980,
      "recommendation": "route_here"
    }
  ]
}
```

### `GET /tools`
List all available tools with their MCP schemas.

### `GET /audit`
Fetch audit logs for your tenant (paginated).

---

## Evaluation Test Cases

Test cases are defined in YAML and measure whether the agent completes a real task correctly:

```yaml
# eval/test_cases/github_workflows.yaml
- id: list_open_issues
  prompt: "List all open issues in my repo gourav/test-repo"
  expected_tool_calls:
    - github_list_issues
  expected_output_contains:
    - "open issues"
  max_latency_ms: 3000
  max_cost_usd: 0.005

- id: create_issue_from_summary
  prompt: "Create a GitHub issue titled 'Fix login bug' with body describing the problem"
  expected_tool_calls:
    - github_create_issue
  success_criteria: output_contains_issue_url
```

---

## Model Routing Logic

After sufficient eval data is collected, the router promotes the cheaper model automatically if quality holds:

```
if (cheaper_model.avg_accuracy >= primary_model.avg_accuracy - 0.05)
   AND (cheaper_model.avg_latency_ms <= primary_model.avg_latency_ms * 1.5):
    route to cheaper_model
```

This is re-evaluated every 100 runs or on explicit trigger via `POST /eval/route`.

---

## Observability

Every run produces a structured log entry:

```json
{
  "run_id": "uuid",
  "tenant_id": "uuid",
  "model": "claude-sonnet-4-6",
  "prompt_hash": "sha256...",
  "cache_hit": false,
  "steps": [
    {
      "step": 1,
      "type": "tool_call",
      "tool": "github_list_issues",
      "latency_ms": 320,
      "status": "success"
    },
    {
      "step": 2,
      "type": "llm_call",
      "tokens_in": 1240,
      "tokens_out": 280,
      "latency_ms": 890,
      "cache_hit": true
    }
  ],
  "total_latency_ms": 1210,
  "total_cost_usd": 0.0019
}
```

---

## Roadmap

- [ ] Streaming agent responses (SSE)
- [ ] Webhook callbacks on run completion
- [ ] Dashboard UI for eval results and cost trends
- [ ] Support for OpenAI function calling format (alongside MCP)
- [ ] Slack integration
- [ ] Self-hosted OAuth app for all integrations

---

## Why This Exists

This project is a reference implementation of the infrastructure problems that production agent platforms solve:

- **Composio** solves the integration gateway problem at scale (250+ apps)
- **LangSmith** solves the eval and observability problem
- **Portkey** solves the model routing and cost problem

AgentGateway combines all three in a single, understandable codebase — built to learn, extend, and ship.

---

## License

MIT

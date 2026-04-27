# GPU router design — `scripts/gpu.py`

The cross-provider GPU router is the "tool" the agent reaches for when
it needs a GPU. This doc is for the next person who extends it (adds
CoreWeave, Lambda, Foundry, etc.) or rewrites a piece of it. Read
`docs/providers-impl-spec.md` first for the per-provider API research;
this doc is about how the pieces fit together.

## Goals

The router exists for three reasons, in priority order:

1. **Survivability under preemption.** Spot capacity vanishes
   unpredictably. A single-provider harness's autonomous run dies the
   first time RunPod preempts you. With ranked fallback across N
   providers, the agent hops and the run survives.
2. **Honest cost accounting.** The dollars budget ceiling is the only
   real-money safety net for an autonomous agent. If the agent can
   spend on a provider whose accruals don't flow into
   `budget_usage[project:<p>:dollars]`, the ceiling is a lie. The
   router's `reconcile` is the only code path that writes the dollars
   counter; every adapter contributes through one shape.
3. **Open-source extension point.** Anyone should be able to add a new
   provider in ~half a day by writing one file and editing one line of
   the registry. No central plan, no breaking changes.

The router is NOT trying to:
- Beat aggregators on price (we use them when convenient — see
  `docs/_internal/market-research/SYNTHESIS.md`)
- Provide reservation pricing or yield-curve optimization (that's a
  Layer-2 ambition we left as a "phase 2" hook via `price_history`)
- Re-architect into a Kubernetes operator (CoreWeave-shaped problems
  belong elsewhere)

## Architecture

```
                     ┌──────────────────────────────────────┐
                     │  scripts/gpu.py    (router + CLI)    │
                     │                                       │
                     │  - discover_providers(env-gated)     │
                     │  - ranked-fallback create            │
                     │  - cooldown filter (preemption_events)│
                     │  - reconcile_all() → budget_usage    │
                     │  - dashboard / cost --json           │
                     └────────┬─────────────┬───────────────┘
                              │             │
              ┌───────────────┼─────────────┼───────────────┐
              │               │             │               │
       ┌──────▼─────┐  ┌──────▼─────┐  ┌────▼──────┐  ┌────▼──────┐
       │ RunPod     │  │ Vast       │  │ Prime     │  │ Verda     │  ... (next)
       │ Provider   │  │ Provider   │  │ Provider  │  │ Provider  │
       │            │  │            │  │           │  │           │
       │ pure API:  │  │ pure API:  │  │ pure API: │  │ pure API: │
       │ no SQL     │  │ no SQL     │  │ no SQL    │  │ no SQL    │
       │ no budget  │  │ no budget  │  │ no budget │  │ no budget │
       └──────┬─────┘  └──────┬─────┘  └────┬──────┘  └────┬──────┘
              │               │             │              │
              └───────────────┴─────────────┴──────────────┘
                              │
                       providers/base.py
                       (Protocol + dataclasses + exceptions)
```

The split is load-bearing: providers are pure API, harness owns state.
This is what lets tests inject `tests/fakes/*` and what makes
`reconcile_all` work uniformly across heterogeneous APIs without each
adapter needing to know about SQLite.

## The Provider Protocol

Every adapter conforms to `providers.base.Provider`:

```python
class Provider(Protocol):
    name: str                               # "runpod", "vast", ...
    supports_bid_auction: bool              # gates spot rank
    supports_pause_preserve: bool           # informs stop vs terminate UX
    preemption_signal: Literal["none", "warning-secs", "hard-kill"]
    billing_url: str                        # surfaced in dashboard

    def auth(self) -> None: ...
    def list_gpus(self, grep) -> list[GpuType]: ...
    def price(self, gpu_type, n) -> Price: ...
    def create_spot(self, spec, *, yes) -> Pod | None: ...
    def list_pods(self) -> list[Pod]: ...
    def get_pod(self, pod_id) -> Pod: ...
    def stop(self, pod_id, *, yes) -> None: ...
    def terminate(self, pod_id, *, yes) -> None: ...
    def resume(self, pod_id, *, yes, bid) -> Pod: ...
    def poll_once(self, pod_id) -> PodStatus: ...
    def current_spend(self) -> Spend: ...
```

Two non-obvious points:

- **Adapters NEVER write SQL or call `budget.py`.** That's the
  harness's job. If you find yourself wanting to do this in an adapter,
  stop and use `Pod.metadata` to surface the data to the harness layer
  instead.
- **`extras: dict` on `SpotSpec`** is the escape hatch for
  provider-specific knobs that don't generalize (RunPod's `secure`,
  Vast's `reliability_min`, Verda's `on_spot_discontinue`). Each
  adapter documents what it reads from `extras`. Don't add per-provider
  fields to the shared dataclasses.

## Discovery

```python
DEFAULT_SPOT_RANK = ["runpod", "vast", "datacrunch", "prime"]
ON_DEMAND_FALLBACK: list[str] = []   # joined only with --allow-on-demand

_PROVIDER_REGISTRY = {
    "runpod":     ("RUNPOD_API_KEY",       "providers.runpod",     "RunPodProvider"),
    "vast":       ("VAST_API_KEY",         "providers.vast",       "VastProvider"),
    "prime":      ("PRIME_API_KEY",        "providers.primeintellect", "PrimeProvider"),
    "datacrunch": ("DATACRUNCH_CLIENT_ID", "providers.datacrunch", "DataCrunchProvider"),
}
```

A provider becomes "configured" when its env var is set in the user's
`.env` (sourced before invoking `gpu.py`). Discovery is silent for
unconfigured providers — that's by design (the user knows they didn't
set the key).

The `--providers <name,name,...>` flag overrides discovery. It accepts:
- Registry slugs (`runpod`, `vast`, `prime`, `datacrunch`)
- Dotted module paths (`tests.fakes.ok`) — used by smoke tests to inject
  mocks. cwd is added to sys.path so paths resolve from the repo root.
- Failures on dotted paths log to stderr (so typos in test invocations
  surface); failures on registry slugs are silent (env not set).

## Ranked-fallback create

`gpu.py create --gpu-type X` does:

1. Discover configured providers (env-gated or `--providers` override)
2. Split into `spot_providers = [p for p in discovered if p.supports_bid_auction]`
   and `on_demand_only = [...]`
3. If `--allow-on-demand` is not set, drop `on_demand_only` entirely
4. Apply cooldown filter: providers with a recent `preemption_events`
   row for `(provider, gpu_type)` are pushed to the BACK of the rank
   (not dropped — we still want a fallback). Window is `COOLDOWN_MIN`
   minutes (default 10).
5. Iterate the rank, calling `provider.create_spot(spec, yes=True)`.
   Catch `OutOfStock | BidRejected | NoCapacity | AuthError |
   ProviderError` and continue. Land at the first success.
6. On success: persist to `gpu_pods` (id, provider, gpu_type, bid,
   project, status='CREATED'); charge budget upper-bound via
   `budget.py add dollars (bid × count × hours)`.
7. If all providers exhaust: exit 3 with `last_err` printed.

## Cross-provider reconcile

`reconcile_all(providers)` is the heartbeat that keeps the budget
honest. It runs:
- On every UserPromptSubmit via `hooks/budget-reconcile.sh` (TTL'd to
  120s default)
- Implicitly inside `gpu.py cost` and `gpu.py dashboard`
- On-demand via `gpu.py reconcile`

Algorithm:

```python
for provider in providers:
    live[provider.name] = {p.id: p for p in provider.list_pods()}

for row in gpu_pods:
    live_pod = live[row.provider].get(row.id)
    if not live_pod:
        row.status = "GONE"     # provider lost track
        continue

    elapsed_hr = (now - row.created_at).total_seconds() / 3600
    compute = row.bid_per_gpu * row.gpu_count
    storage = STORAGE_RATE_PER_GB_HR * (live_pod.metadata.disk_space or 0)

    if live_pod.status == "RUNNING":
        rate = compute + storage
    else:
        rate = compute * 0.5 + storage   # conservative for EXITED

    row.accrued_dollars = elapsed_hr * rate

# Sum into budget_usage[project:<p>:dollars]
for project, total in gpu_pods.group_by(project).sum(accrued_dollars):
    upsert budget_usage(key=f"project:{project}:dollars", value=total)
```

Two design choices worth understanding:

1. **bid_per_gpu as the rate proxy.** We use the bid-at-create as the
   per-pod rate, not the live `cost_per_hr` from each provider's API.
   This is conservative (rates can drop after create; we'd over-count)
   and uniform (every adapter populates `bid_per_gpu` reliably; live
   rates are inconsistent). Bias: budget errs toward blocking sooner.
2. **Half-compute for EXITED.** When a pod exits before we know exactly
   when, we charge half the elapsed-time at compute rate. Over-counts
   on quick exits, under-counts on long-running pods that just exited.
   In practice the second case is rare because reconcile runs every
   2 min — quick to catch.

## Cooldown via `preemption_events`

Schema (migration 004):

```sql
CREATE TABLE preemption_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  pod_id      TEXT,                                    -- nullable
  provider    TEXT NOT NULL,
  gpu_type    TEXT NOT NULL,
  ts          TEXT NOT NULL DEFAULT (datetime('now')),
  reason      TEXT
);
CREATE INDEX idx_preemption_events_lookup ON preemption_events(provider, gpu_type, ts);
```

Written by:
- `reconcile_all` when it observes a `intended=running, actual!=running`
  transition on a pod it knows about (and idempotent-bounded to one row
  per pod per 5 minutes)
- Adapter `poll_once()` calls during autopilot loops (future hook;
  currently optional)

Read by `_on_cooldown(provider, gpu_type)` in the create router. Default
window 10 min. The choice of "demote to back of rank" rather than "drop
from rank" is deliberate: with all spot providers in cooldown, we still
want a fallback rather than failing the create.

## Dashboard / cost surfaces

Two surfaces, same data:

- **`gpu.py cost --json`** — LLM-ergonomic structured summary. Used by
  the `/gpu-spend` skill. Returns
  `{project, providers: [...], grand_total_per_hr, grand_cumulative_usd}`.
  Each provider entry includes `billing_url` so the agent can suggest a
  click-through link in summaries.
- **`gpu.py dashboard`** — human box-drawn one-screen view. Same data
  plus visual hierarchy: status icons, idle-storage warning, budget
  gauge, recent preemption events, reconcile freshness.

Both reconcile silently before reporting so cumulative numbers reflect
current reality. `billing_url` is a Provider class attribute so the
dashboard renders provider links without an external lookup table.

## How to add a new provider

This is the workflow that delivered RunPod, Vast, Prime, Verda. ~half
a day per adapter once you've absorbed the Protocol shape.

**1. Research the API.** Read `docs/providers-impl-spec.md` for the
template, then write a short survey under
`docs/_internal/market-research/` covering: auth shape, list/price/create/
get/stop/terminate endpoints, request body field names, error
taxonomy mapping, SSH key handling, any gotchas. If the provider has an
OpenAPI spec, parse it programmatically — saves a round of correction.

**2. Write `providers/<name>.py`.** Match the shape of `vast.py` or
`runpod.py`. Targets:
- `~280-400 LOC` — if you're past 500, you're probably leaking concerns
  the harness should own
- Pure API: no SQLite imports, no `budget.py` calls, no `sys.exit`
- Raise from `AuthError | OutOfStock | BidRejected | NoCapacity |
  ProviderError` — the router catches these by type
- Document `extras` keys the adapter reads in the module docstring

**3. Register in `gpu.py`.** Add a row to `_PROVIDER_REGISTRY`:
```python
"<name>": ("<ENV_VAR>", "providers.<name>", "<ClassName>"),
```
And add to `DEFAULT_SPOT_RANK` if it has a spot tier; otherwise to
`ON_DEMAND_FALLBACK` only if it offers something unique enough to
justify the on-demand premium.

**4. Document in `.env.example`.** Add a section with signup URL,
billing prerequisite, SSH key flow, env var(s) the user needs to set.

**5. Add to `install.sh` credential wizard.** Define a `_probe_<name>`
function that does a curl against an auth endpoint, then call
`_wizard_setup_one`. For OAuth2 providers (like Verda), print manual
guidance instead — the wizard's per-provider helper assumes one env var.

**6. Write a `skills/<name>/SKILL.md`.** Frontmatter with a description
that triggers on user mentions of the provider. Body explains: when to
invoke (vs `/gpu-spend`), tools available (CLI if any, plus
`gpu.py --providers <name>`), decision tree, peculiarities, billing URL.

**7. Verify Protocol conformance.** A tiny test:
```python
from providers.<name> import <ClassName>
from providers.base import Provider
inst = <ClassName>()
assert isinstance(inst, Provider)  # runtime_checkable Protocol
```

**8. Smoke-test against fakes** (no live API). Already covered by
`tests/fakes/*` if your adapter conforms; you don't need to add
adapter-specific tests unless the adapter has unusual behavior.

**9. Dogfood.** Sign the user up for an account if needed (this is the
slow part — gate keys come from the human), provision the cheapest
GPU available for ~5 min, verify the round-trip, terminate. Budget $2
max per dogfood. **Wrap in `try/finally: terminate(...)` always** — the
single most expensive mistake is leaving a pod running after a test.
See `memory/feedback_provider_api_testing.md` for the discipline rules.

**10. Commit and push.** One commit per adapter, `feat:` prefix.
Smoke test must stay green.

## What's deliberately deferred

- **Layer 2: price intelligence.** A `price_history` cron-logged table
  every 30 min per (provider, gpu_type, region) would let us detect
  price spikes ("min_bid is unusually high vs. trailing 24h, wait
  before creating") and predict preemption rates per-pair. The schema
  hook is mentally there; nobody's wired the cron yet.
- **Layer 3: bid optimization.** Given a job's `--hours N`, compute the
  bid that minimizes `expected_cost = bid × hours × P(survive_N) +
  recovery_cost × (1 - P(survive_N))`. Requires Layer 2 data first.
- **Layer 4: provider switching mid-run.** Hard — requires
  checkpoint/restore. Not on roadmap.

## Reference

- Protocol & dataclasses: `project-harness/scripts/providers/base.py`
- Router: `project-harness/scripts/gpu.py`
- Per-provider adapters: `project-harness/scripts/providers/{runpod,vast,primeintellect,datacrunch}.py`
- Schema: `project-harness/memory/migrations/00{2,3,4}_*.sql`
- Test fakes: `tests/fakes/*.py`
- Smoke assertions: `tests/smoke-test.sh` (section "gpu.py router with fake providers")
- Setup guide: `docs/providers-setup.md`
- Implementation spec for next adapters: `docs/providers-impl-spec.md`
- Market research: `docs/_internal/market-research/{SYNTHESIS,pricing-matrix,aggregator-economics,direct-adapter-feasibility}.md`

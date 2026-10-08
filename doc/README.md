# Documentation index

Short, current documents that humans and AI agents both read. Each file has one job.

| File | Job | Updated when | Limit |
|---|---|---|---|
| [goals.md](goals.md) | Why the backend exists, scope, non-goals, success criteria | Goals change (rare) | ~80 lines |
| [architecture.md](architecture.md) | How it is built now: components, data model, environments | Structure changes | ~150 lines |
| [status.md](status.md) | What works today, what is in progress, known issues | Every merged PR | ~60 lines |
| [roadmap.md](roadmap.md) | Ordered phases with acceptance criteria | A phase starts or ends | ~120 lines |
| [decisions/](decisions/) | ADRs: one decision per file, never rewritten, only superseded | A lasting decision is made | ~40 lines each |
| [tasks/](tasks/) | Assignments for the implementer agent, with architect review | Per task | ~120 lines each |

## Rules for keeping docs useful

- **Current state only** in goals, architecture, status and roadmap. History belongs in ADRs and git log.
- **No duplication.** Link instead of copying. Business strategy and website copy live outside this repo
  (owner's Claude project docs); link to them, do not paste them.
- **Write for a cold reader**: an agent with no chat history must be able to act from these files alone.
- **Stay under the limits.** Short files fit an agent's context without crowding out the code. If a file
  grows past its limit, cut or split it.
- Changing direction: add a new ADR with status `Accepted` and mark the old one `Superseded by 00xx`.

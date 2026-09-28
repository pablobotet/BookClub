# Project Instructions

## Working agreement

- Read the relevant files before proposing or making changes.
- Keep changes small and focused on the requested outcome.
- Do not edit generated files, secrets, or unrelated work from other contributors.
- Before finishing, inspect the diff and run the most relevant available checks.
- If the project has no tests or build command, state that explicitly and perform the strongest available validation.

## Agent workflow

For non-trivial requests, use the `orchestrator` primary agent configured in `opencode.json`, normally through `/flow`.

The coordinator must:

1. Inspect the repository and convert the request into independently verifiable tasks.
2. Dispatch one implementation agent per task, sequentially when tasks touch the same files.
3. Dispatch a verifier after every implementation task.
4. Feed verifier findings back to the implementation agent for a limited fix loop.
5. Stop after three verification rounds for one task and ask for clarification if the result is still blocked.

Never claim success when checks are failing or when verification was skipped.

Planning is part of the coordinator; there is no separate planning subagent.

The `quick-change` primary agent is reserved for explicit, small, localized work and must not be dispatched by the coordinator.

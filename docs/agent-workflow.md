# OpenCode Agent Workflow

The project uses OpenCode's native agent configuration in `opencode.json`. Agent prompts live in `.opencode/prompts/` and are referenced with OpenCode's `{file:...}` syntax.

## Architecture

- `orchestrator`: primary agent using `ibm1/gpt-5.6-sol` with high reasoning. It inspects the repository, plans and coordinates work, but cannot edit files.
- `implementer`: subagent using `ibm1/gpt-5.6-terra`. It receives one task and can edit and validate it.
- `verifier`: read-only subagent using `ibm1/gpt-5.6-terra`. It returns `PASS`, `FAIL`, or `BLOCKED`.
- `quick-change`: separate primary agent using `ibm1/gpt-5.6-luna` for small direct edits. It cannot delegate.
- `chat`: isolated primary agent using `ibm1/gpt-5.6-luna` for questions and informal consultation. It only receives the current conversation and has no project, shell, web, skill, or delegation access.

OpenCode does not load standalone JSON files per agent. Its supported JSON form is the `agent` object inside `opencode.json`; the alternative is one Markdown file per agent in `.opencode/agents/`. This project uses the JSON form so model and permission settings remain centrally validated by the official schema.

## Coordinated Work

Run:

```text
/flow Add the requested feature or fix
```

You can also select the `orchestrator` primary agent and describe the request normally. The loop is bounded to three implementation-verification rounds per task.

The orchestrator plans the work itself and can invoke only `implementer` and `verifier`. Subagents cannot delegate further because `subagent_depth` is `1` and their `task` permission is denied.

## Small Personal Changes

Switch to the `quick-change` primary agent with the agent selector, usually using `Tab`, and request the edit directly. It is intentionally excluded from the coordinated workflow.

Use it for small documentation edits, simple configuration, or straightforward localized fixes. For ambiguous, cross-cutting, security-sensitive, migration, or multi-task work, use `/flow` instead.

## Conversation-only Questions

Switch to the `chat` primary agent with `Tab` when you want to ask questions using only the current conversation as context. It cannot inspect or modify the project, execute commands, browse external sources, load skills, or invoke subagents.

If a question needs information that is not already in the conversation, provide that information directly or switch to an agent with the required access.

## Model Configuration

The model IDs are exact entries reported by `opencode models` in this environment:

- `ibm1/gpt-5.6-sol`
- `ibm1/gpt-5.6-terra`
- `ibm1/gpt-5.6-luna`

The orchestrator passes `reasoningEffort: high` through the agent `options` field.

## Reloading

OpenCode loads configuration when it starts. Quit and restart OpenCode after changing `opencode.json` or any prompt file.

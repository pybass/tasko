---
name: tasko
description: Read, add, and update the user's tasks in tasko, their personal task manager. Use when the user asks to save a task for later, show open tasks, pick a task to work on, or mark one done.
---

The user's tasks live in tasko. Use the `tasko` CLI and always pass `--json`.

tasko is shared: the user reads and edits the same tasks in a terminal UI,
and agents reach them through the CLI. Write every task for the person
first.

If `tasko` is missing or rejects these commands, stop and tell the user to
install or upgrade tasko. Never read or write the database directly.

## Project

A tasko project matches a repository. The project name is the name of the
git root directory: `basename "$(git rev-parse --show-toplevel)"`. Pass it
with `-p`.

If `tasko projects --json` has no such project, ask the user which project
to use. Never guess, and never fall back to another project.

## Commands

```
tasko list -p PROJECT --json          # open tasks; add --all for done ones
tasko show ID --json
tasko add TITLE -p PROJECT --body TEXT --json
tasko edit ID [--title T] [--body TEXT] [--priority low|medium|high] [-p PROJECT] --json
tasko status ID todo|doing|done --json
tasko projects --json
```

`add`, `edit`, and `status` print the resulting task. `edit --body` replaces
the whole body; read the task first when you need to keep part of it.

## Adding a task

1. Add a task only when the user asks. You may suggest one; do not create
   it on your own.
2. First run `tasko list -p PROJECT --json`. If an open task already covers
   it, say so and offer to update that task instead.
3. One task is one result that can be finished and checked. Split a request
   that names several.
4. A task that is not about the current repository goes to the default
   project: omit `-p`.
5. Leave the priority alone unless the user names one.
6. Write the title and body in the language the user speaks.
7. Tell the user the id and project of every task you wrote.

### Title

The user finds the task by its title in one list across all projects.

- Name the result, in the user's own words where possible.
- At most 60 characters. No period, no project name, no prefix such as
  "TODO" or "fix:".

### Body

Keep the body as short as the task allows; many tasks need none.

- Write only what the code cannot tell a later reader: the goal, when the
  title does not make it clear; a decision already made, with its reason;
  a place to look that is not obvious.
- Evidence belongs in the body: quote an error message, a log, or a command
  exactly, in a code block. Trim it to the lines that matter.
- Never write a plan, steps, or the story of the discussion. Whoever does
  the task will plan it against the code as it is then.
- Write only what the conversation or the code established. Never invent a
  reason.
- Your own words stay short plain prose: no headings, no lists, no
  checklists. Name files by path from the repository root and functions by
  name, without line numbers.
- It must stand alone: no "as discussed", "this bug", "the above".
- Go longer only when the user asks for detail.
- No secrets.

## Working on a task

1. Read it first: `tasko show ID --json`.
2. Change the status only when the user asks. When the work is finished,
   offer to mark the task done; do not mark it yourself.

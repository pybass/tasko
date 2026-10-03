---
name: tasko
description: Read, add, and update the user's tasks in tasko, their personal task manager. Use when the user asks to save a task for later, show open tasks, pick a task to work on, or mark one done.
---

Use the `tasko` CLI with `--json`. Never read or write the database directly.
If the CLI is missing or a command fails, report the problem. Suggest
installing or upgrading only for a missing CLI or unsupported command.

## Writing tasks

The user reads tasks in a terminal UI. Keep them brief by default.
Always write titles and bodies in simple English, whatever language the
user speaks. Use common words and short sentences. Keep logs, errors,
commands, and quotes unchanged.

### Title

Name the main result in at most 60 characters. No period, project name,
or prefix such as "TODO" or "fix:". One task should cover one result;
separate independent requests.

### Body

Leave the body empty when the title is enough. Otherwise, briefly capture
the main idea so a person can understand the task without the chat.
The agent who works on it will investigate and plan the work then.

Include a detail only when leaving it out could change the intended result
or lose an essential constraint. Do not add a plan, investigation history,
file list, or every point from the discussion just because it is available.
A long discussion does not call for a long body.

When the user asks to save a detailed plan, requirements, logs, or other
material, preserve the requested detail. A large body is also fine when
needed evidence or precise requirements demand it. There is no fixed length
limit or required format; use prose, lists, or code blocks as needed.

Keep only established facts and decisions. Do not turn suggestions into
requirements or invent reasons. Never include secrets.

## Choosing a project

Use the project the user explicitly names. Otherwise, use the name of the
current Git root directory, found with `git rev-parse --show-toplevel`.
Check the name with `tasko projects --json`. If there is no matching project
or no repository, ask which project to use; never silently use another.

Use the default project only when the user explicitly asks for it. Omit
`-p` on `add` for that request. Find its name from the project with
`is_default: true` in `tasko projects --json`, and use that name when
checking for duplicates. Do not assume it is named "default" or "inbox".

## Adding and updating

- Add or change tasks only when the user asks. Leave priority and status
  alone unless requested, including when starting or finishing work.
- Before adding, list open tasks in the chosen project with
  `tasko list -p PROJECT --json`. This applies to the default project too.
  If a task seems to cover the same result, show its id and title and offer
  to update it. Similar titles alone do not make duplicates; the user may
  still want a separate task.
- Before working on or editing a task, read it with `tasko show ID --json`.
  If several tasks fit the request, ask which one. Change only requested
  fields. `edit --body` replaces the whole body, so keep existing details
  that the requested edit does not affect.
- After a write succeeds, tell the user the task id and project. The write
  commands return the resulting task.

## Commands

```
tasko list [-p PROJECT] [--all] --json
tasko show ID --json
tasko add TITLE [-p PROJECT] [--body TEXT] [--priority low|medium|high] --json
tasko edit ID [--title T] [--body TEXT] [--priority low|medium|high] [-p PROJECT] --json
tasko status ID todo|doing|done --json
tasko projects --json
```

`list` shows open tasks; `--all` includes done ones. Without `-p`, `list`
shows every project, while `add` uses the default project. `edit -p` moves
a task to that project. `edit --body ""` clears its body.

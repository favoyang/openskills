---
name: loop-scheduler
description: Create recurring Codex workflows by choosing between fresh scheduled tasks and current-thread scheduled messages. Use when the user asks to set up a recurring check, monitor, reminder, loop, scheduled work item, or periodic follow-up and needs help deciding what should run, when to report, when to stop, and when to ask for input.
---

# Loop Scheduler

## Overview

Create scheduled Codex workflows that repeat with the right amount of context. Decide first whether each run can start fresh or whether the next run needs this thread's current context, then create the matching scheduled workflow.

## Decision

Use a **Scheduled Task** when each run can start fresh from a durable prompt and any discoverable external state. Examples: check a website weekly, summarize new GitHub issues, monitor a feed, remind the user to review something, or run a repeated status query.

Use a **Scheduled Message** when the next run needs the current thread's context, unresolved decisions, local reasoning, draft state, or prior conversation. Examples: continue this investigation tomorrow, check whether the user replied with missing input, revisit a plan after a waiting period, or follow up on an in-progress thread.

If both could work, prefer Scheduled Task for independent monitoring and Scheduled Message for conversational continuity.

## Workflow

1. Infer as much as possible from the conversation: target, cadence, reporting threshold, stop condition, and when user input is required.
2. Ask only questions whose answers materially change the scheduled workflow:
   - What should Codex do each time?
   - How often should it run?
   - What change is important enough to report?
   - When should it stop?
   - When should it ask me for input?
3. Keep questions concise and omit any question already answered or safely inferable.
4. Create the scheduled workflow using the available automation tool. If the tool is not already available, discover the automation update tool first.
5. Use a short, durable prompt that makes sense on a later run without relying on hidden assumptions.

## Prompt Rules

Write the scheduled prompt so a future Codex run can act without re-reading this setup thread unless it is a Scheduled Message. Include:

- The task to perform each run.
- The cadence or timing requirement.
- The specific reporting threshold.
- The stop condition, if any.
- The user-input condition, if any.

Avoid vague prompts such as "check this again" or "continue monitoring." Prefer concrete wording such as "Every weekday morning, check open PRs assigned to me and report only new failing required checks or PRs blocked for more than 24 hours. Stop after all listed PRs are merged."

## Confirmation

After creating the workflow, summarize the type chosen, schedule, reporting threshold, stop condition, and the exact prompt used.

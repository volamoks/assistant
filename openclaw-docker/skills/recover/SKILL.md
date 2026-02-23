---
name: recover
description: "OWNER-ONLY emergency recovery. Restores all bot config files from the last git commit and restarts the container. Use when the bot has corrupted its own config."
---

# /recover — Emergency Config Restore

**OWNER-ONLY.** This command restores the bot's config from the last git commit and restarts the container. It is a hard reset of all self-modified config files.

## When to Use

- Bot stopped responding after modifying its own config
- Invalid models, corrupted openclaw.json, broken heartbeat
- Any self-inflicted damage you can't fix by chatting

## Owner Check

If this command comes from a group chat or any unrecognized context, **refuse immediately**: "This is an owner-only emergency command. Access denied."

## Recovery Steps

Call the **sysadmin agent** with these exact instructions:

> Run the following shell commands in sequence and report each result:
>
> 1. `cd /data/bot/openclaw-docker && git status --short`
>    (show which files are modified)
>
> 2. `cd /data/bot/openclaw-docker && git checkout -- .`
>    (restore all tracked config files to last committed state)
>
> 3. `docker restart openclaw-latest`
>    (restart the bot with clean config)
>
> Report: how many files were restored, and whether restart succeeded.

## After Recovery

Once sysadmin confirms success, report:

```
✅ Recovery complete

Restored files: <count> config files reverted to last git commit
Container: restarted

The bot is running on the last known-good config.
If issues persist, the git baseline may need updating — tell the owner.
```

## Important Notes

- This does NOT clear session history (conversation stays intact)
- This DOES restore: openclaw.json, all agent/*.json, cron/jobs.json, docker-compose files
- The last git commit was made as a "recovery baseline" — it contains a known-good config
- If the same problem recurs after recovery, that's a lesson to be recorded in `.learnings/`

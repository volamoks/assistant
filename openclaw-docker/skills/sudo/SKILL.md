# /sudo — Elevated Access Request

## When to use
Agent needs root/elevated privileges to perform a system operation:
- Install pip packages with pip install
- Restart Docker containers
- Modify system files
- Run commands requiring sudo

⚠️ **NEVER execute elevated commands without user approval!**

## Workflow

### Step 1: Request Permission
When you need elevated access:

1. Call bash with the sudo_approve.sh script:
   ```bash
   bash /data/bot/openclaw-docker/scripts/sudo_approve.sh request "<command>"
   ```

2. Extract the token from the output

3. Ask user for approval with clear context:
   ```
   🔐 **Sudo Request**
   
   Need elevated access for:
   `pip install telethon`
   
   Token: `1718961234:abc123:abc12345`
   
   Reply with:
   • `/sudo approve` — to allow
   • `/sudo deny` — to reject
   ```

### Step 2: Wait for Approval
Do NOT execute the command yet. Wait for user response.

### Step 3: Check Approval
After user approves:

```bash
bash /data/bot/openclaw-docker/scripts/sudo_approve.sh check <token>
```

If successful (exit code 0):
- Execute the command
- Report result to user

If denied or expired:
- Inform user the request was denied/expired
- Do NOT execute the command

### Step 4: Execute (if approved)
Once sudo is granted:

```bash
# Execute the approved command
sudo pip install telethon
```

Report result:
```
✅ Command executed successfully!
Output: [result]
```

## Important Rules

1. **Always explain WHY** — Tell user exactly what the command does
2. **Show the exact command** — Don't hide what will run
3. **One token = one command** — Don't try to chain multiple commands
4. **Token expires in 5 minutes** — If not used, request again
5. **Log everything** — All approvals/denials are logged

## Security Considerations

- Commands are logged with timestamp and token
- User can audit all requests with `/sudo list`
- Tokens are one-time use only
- Expired tokens are automatically rejected

## Examples

### Example 1: Install Python package
```
Agent: "Для установки telethon нужен sudo. Разрешаешь?"
User: "/sudo approve"
Agent: *checks token* → executes → "Готово! telethon установлен"
```

### Example 2: Restart container
```
Agent: "Хочу перезапустить контейнер Prowlarr. Команда: docker restart prowlar"
User: "Да"
Agent: *checks token* → executes → "✅ Контейнер перезапущен"
```

### Example 3: User denies
```
Agent: "Нужен sudo для rm -rf /tmp/cache. Разрешаешь?"
User: "/sudo deny"
Agent: "❌ Запрос отклонён. Команда не будет выполнена."
```

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| "No sudo token found" | No pending request | Create new request first |
| "Token expired" | >5 minutes passed | Create new request |
| "Token mismatch" | Wrong token provided | Check correct token |
| "Already a pending request" | Another request active | Wait or clear first |

## Telegram Commands (for user)

User can also manage requests directly:

- `/sudo status` — View current pending request
- `/sudo approve` — Approve pending request  
- `/sudo deny` — Deny pending request
- `/sudo list` — View audit log
- `/sudo clear` — Clear all requests
- `/sudo help` — Show help

# web_clip

Clips any web page to clean Markdown and saves it to Obsidian vault.

## Tool: web_clip

Fetches a URL, strips HTML/JS/CSS, converts to clean Markdown, saves to Obsidian.

### Usage

```bash
bash /data/bot/openclaw-docker/scripts/web_clip.sh "<URL>" <max_chars> <save>
```

### Arguments

- `URL` (string, required): Page to clip
- `max_chars` (number, optional, default=4000): Max text length — controls how many tokens used  
- `save` (true/false, optional, default=true): `true` saves to Obsidian, `false` prints only

### Returns

- If `save=true`: confirmation with saved path and word count
- If `save=false`: clean markdown text of the page

### Saved to

`/data/obsidian/To claw/Web Clips/YYYY-MM-DD-<title>.md`

### Token-saving tips

- Use `max_chars=2000` for quick reads (no save needed)
- Use `max_chars=4000` for saving full articles
- `save=false` when you just want to summarize content inline

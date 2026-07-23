# PS5 Stock Alert Bot

Checks product pages every 10 minutes and sends you a Telegram message
the moment a tracked PS5 listing goes from out-of-stock to in-stock.

## Setup (one-time, ~10 minutes)

### 1. Create a GitHub repo
- Go to github.com → New repository (can be private) → name it e.g. `ps5-stock-alert`
- Upload all files from this folder into it (drag-and-drop works on github.com,
  or use `git push` if you're comfortable with git)

### 2. Add your Telegram credentials as secrets (NOT in the code)
In your new repo:
- Go to **Settings → Secrets and variables → Actions → New repository secret**
- Add secret named `TELEGRAM_BOT_TOKEN` → paste your bot token
- Add secret named `TELEGRAM_CHAT_ID` → paste your chat ID

This keeps your credentials encrypted and out of the visible code, even if
the repo is public.

### 3. Enable Actions
- Go to the **Actions** tab in your repo → click "I understand my workflows,
  enable them" if prompted.
- The workflow will now run automatically every 10 minutes.
- To test it immediately: Actions tab → "PS5 Stock Checker" → "Run workflow"

### 4. Add more products
Open `check_stock.py` and add entries to the `PRODUCTS` list near the top,
following the existing Flipkart example. Set `"type"` to `"flipkart"`,
`"amazon"`, or `"croma"` depending on the site.

## Notes & limitations

- **Amazon and Flipkart actively try to block automated requests.** This
  script uses browser-like headers to reduce blocks, but if a site tightens
  its detection, a run may fail to fetch the page. The script logs this and
  simply skips that run rather than sending a false alert — it'll pick back
  up on the next successful check.
- If a listing's stock text ever comes back as "UNKNOWN" in the logs, the
  site likely changed its page layout slightly, and the keyword matching in
  `check_flipkart` / `check_amazon` / `check_croma` may need a small update.
- You can watch logs anytime under the Actions tab → click into a run.
- GitHub free tier gives you 2,000 Action minutes/month, which easily covers
  checks every 10 minutes.

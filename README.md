# Error Fare Alert Bot (100% free)

This checks flight-deal sites every 30 minutes and messages you on Telegram
when a new post matches your destinations. It costs nothing and needs no
server — it runs on GitHub's free automation (GitHub Actions).

## What you need
- A Telegram account (free)
- A GitHub account (free) — https://github.com/join

## Step 1 — Create your Telegram bot (2 minutes)
1. Open Telegram, search for **@BotFather**, start a chat with it.
2. Send `/newbot`, give it a name and a username (must end in "bot").
3. BotFather replies with a **token** — a long string like
   `123456789:AAExampleTokenHere`. Copy it, you'll need it in Step 3.
4. Now search for the bot you just created (by the username you gave it)
   and send it any message, e.g. "hi". This "activates" your chat with it.

## Step 2 — Get your chat ID
1. In your browser, go to:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   (replace `<YOUR_TOKEN>` with the token from Step 1)
2. Look for `"chat":{"id":123456789,...}` in the response — that number is
   your **chat ID**. Copy it.

## Step 3 — Create the GitHub repository
1. Log into GitHub, click **New repository**, name it e.g. `error-fare-bot`,
   set it to **Private**, create it.
2. Click **Add file → Upload files**, and drag in every file from this
   folder (keep the `.github/workflows` folder structure intact).
3. Commit the files.

## Step 4 — Add your secrets
1. In your repo, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**, add:
   - Name: `TELEGRAM_BOT_TOKEN` → Value: the token from Step 1
   - Name: `TELEGRAM_CHAT_ID` → Value: the chat ID from Step 2

## Step 5 — Turn it on
1. Go to the **Actions** tab of your repo. GitHub may ask you to enable
   Actions — click enable.
2. Click into "Check flight deals" → **Run workflow** to test it manually.
3. Check Telegram — you should get any matching deals posted recently.
4. From now on it runs automatically every 30 minutes, for free, forever
   (GitHub's free tier gives 2,000 minutes/month of Actions time; this job
   uses well under 1% of that).

## Customizing what you get alerted on
Edit `config.json`:
- `"destinations"`: list of cities/countries/keywords to match against post
  titles and summaries. Leave it as `[]` to get every deal, unfiltered.
- `"only_error_fares"`: set to `true` to only alert on posts whose text
  contains language like "error fare", "mistake fare", or "glitch" — this
  cuts out regular (non-error) cheap-flight posts.

Just edit the file in GitHub (pencil icon), commit, and it takes effect on
the next run — no need to touch anything else.

## Adding more sources
Add more RSS feed URLs to the `FEEDS` list in `fetch_and_alert.py`. Good
candidates to look for: any flight-deal blog that has a "Follow via RSS"
option (search "[site name] rss feed").

## Phase 2 — Price scoring + savings % (already built in)

`check_routes.py` checks specific routes you configure directly against
Travelpayouts price data, and sends you a **scored** alert with a real
savings percentage — it doesn't wait for a blog to post about it.

### Step A — Get a free Travelpayouts token
1. Go to https://www.travelpayouts.com/programs/100/tools/api and sign up
   for a free affiliate account (no cost, no card).
2. Once approved, copy your API token from that page.
3. Add it as a new GitHub secret: `TRAVELPAYOUTS_TOKEN` (same place as
   Step 4 above).

### Step B — Add routes to watch
Edit `config.json`'s `"routes"` list with 3-letter airport codes, e.g.:
```json
"routes": [
  { "origin": "JFK", "destination": "CDG" },
  { "origin": "LAX", "destination": "NRT" }
]
```
`min_savings_percent` controls how big a discount (vs. that route's recent
average price) is needed before you get pinged — 40 is a reasonable start.

The workflow now runs both checks every 30 minutes automatically.

## Phase 2 — GUI (app.py)

Instead of hand-editing `config.json`, `app.py` is a small Streamlit web
app with validated form fields for destinations, routes, and notification
settings — invalid input (wrong airport code format, bad token shape, etc.)
is rejected immediately with a specific error message.

### Deploy it for free
1. Go to https://share.streamlit.io and sign in with your GitHub account.
2. Click **New app**, pick your `error-fare-bot` repo, branch `main`,
   file path `app.py`.
3. Click **Deploy** — you'll get a free public URL for your config GUI.
4. Use the app to build your config, click **Download config.json**, then
   upload it into your GitHub repo (replacing the existing one).

Note: the GUI edits and exports `config.json` for you to upload — it does
not auto-push to GitHub or store your bot tokens (those stay in GitHub
Secrets only, never in the app or in config.json). This keeps your
credentials out of any public-facing surface.

## Security notes (for your reviewer)
- No credentials are stored in code or in `config.json` — only in GitHub's
  encrypted Secrets, injected as environment variables at runtime.
- The Streamlit GUI never transmits or stores tokens; token fields are used
  only for local format validation in the browser session.
- Only public, documented third-party APIs are called (Travelpayouts,
  Telegram Bot API, public RSS feeds) — no scraping behind logins.
- `seen.json` / `route_seen.json` store only public post IDs / route-price
  identifiers, no personal data.
- Suggested hardening if you take this further: pin dependency versions in
  `requirements.txt`, add request timeouts/retries (timeouts are already
  set to 15s), and rotate the Telegram/Travelpayouts tokens periodically.

# LinkedIn Auto-Poster

Automated LinkedIn posting system with JSON-based queue scheduling. Define your posts in a queue file with scheduled dates and times, and a cron job handles publishing them to LinkedIn via the REST API.

## How It Works

1. A JSON queue file defines posts with scheduled dates, times, content, and optional hashtags
2. A cron job runs the poster script every 15 minutes during posting hours
3. Each run publishes at most one post (avoids flooding your connections' feeds)
4. Published posts are marked as completed with the LinkedIn post URN and timestamp
5. Supports two post types: **opinion posts** (text only) and **article shares** (with links)

## Features

- **`--dry-run`** -- Preview what would be posted without actually publishing
- **`--force ID`** -- Post a specific queue item immediately, regardless of schedule
- **`--status`** -- View a summary of queued, posted, and failed items
- **Automatic hashtag appending** -- Hashtags defined per post are appended cleanly
- **Token refresh support** -- Reads access token from a JSON file (swap in a refreshed token at any time)
- **One-post-per-run throttling** -- Only the first due post is published per execution

## Setup

### 1. Create a LinkedIn App

Go to [developers.linkedin.com](https://developers.linkedin.com/) and create an app. You need:

- **OAuth 2.0 redirect URL** -- Set to `http://localhost:5000/linkedin/callback` for local dev
- **Products** -- Request access to "Share on LinkedIn" (grants `w_member_social` scope)

### 2. Get an OAuth Token

Use the included `oauth_callback_example.py` to run the OAuth flow locally:

```bash
pip install flask requests

# Edit CLIENT_ID and CLIENT_SECRET in oauth_callback_example.py
python3 oauth_callback_example.py
```

Open the printed authorization URL in your browser, approve access, and the script saves your token to `linkedin_token.json`.

### 3. Configure Your Queue

Copy the example queue and customize it:

```bash
cp example_queue.json linkedin_queue.json
```

Edit `linkedin_queue.json`:

- Set `config.member_urn` to your LinkedIn member URN (`urn:li:person:YOUR_ID`)
- Set `config.token_path` to the absolute path of your token JSON file
- Add posts with `scheduled_date`, `scheduled_time`, and `text`

### 4. Install the Cron Job

```bash
# Post during business hours, every 15 minutes (Mon-Fri 8am-6pm)
crontab -e

*/15 8-17 * * 1-5 /usr/bin/python3 /path/to/linkedin_poster.py >> /path/to/linkedin_poster.log 2>&1
```

## Queue Format

Each post in the queue has:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g., `opinion-01`, `article-03`) |
| `type` | `opinion` (text only) or `article` (includes a link) |
| `scheduled_date` | Date to publish (`YYYY-MM-DD`) |
| `scheduled_time` | Time to publish (`HH:MM`, 24-hour) |
| `status` | `queued`, `posted`, or `failed` |
| `text` | The post content |
| `hashtags` | List of hashtags to append (e.g., `["#DataStrategy", "#AI"]`) |
| `posted_at` | Timestamp when posted (filled automatically) |
| `post_urn` | LinkedIn post URN (filled automatically) |

## Usage

```bash
# Preview what would post right now
python3 linkedin_poster.py --dry-run

# Check queue status
python3 linkedin_poster.py --status

# Force-post a specific item
python3 linkedin_poster.py --force opinion-01

# Normal run (cron calls this)
python3 linkedin_poster.py
```

## Content Strategy Notes

**Use 2 opinion posts for every 1 article share.** Opinion posts (pure text, no external links) consistently get more algorithmic reach on LinkedIn because they keep users on-platform. Article shares with links get suppressed in the feed algorithm.

A good cadence:

- Monday: Opinion post
- Wednesday: Article share (with link)
- Friday: Opinion post

This gives you 3 posts per week with a 2:1 opinion-to-article ratio.

## Tech Stack

- **Python 3** -- Single-file script, minimal dependencies
- **LinkedIn REST API** -- v202601, using the `/rest/posts` endpoint
- **OAuth 2.0** -- Standard authorization code flow with `w_member_social` scope
- **cron** -- System scheduler for automated runs
- **requests** -- HTTP client (only external dependency)

## Requirements

```
requests
flask  # only needed for oauth_callback_example.py
```

## License

MIT

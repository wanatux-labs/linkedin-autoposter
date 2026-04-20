#!/usr/bin/env python3
"""
LinkedIn Auto-Poster
Reads from linkedin_queue.json, posts any items due, marks them posted.
Run via cron every 15 minutes during posting hours.

Usage:
    python3 linkedin_poster.py              # post anything due now
    python3 linkedin_poster.py --dry-run    # preview what would post
    python3 linkedin_poster.py --force ID   # post a specific item now
    python3 linkedin_poster.py --status     # show queue status
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
QUEUE_PATH = SCRIPT_DIR / "linkedin_queue.json"
LOG_PATH = SCRIPT_DIR / "linkedin_poster.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("linkedin_poster")


def load_queue() -> dict:
    with open(QUEUE_PATH) as f:
        return json.load(f)


def save_queue(data: dict) -> None:
    with open(QUEUE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_token(token_path: str) -> str:
    with open(token_path) as f:
        return json.load(f)["access_token"]


def build_post_body(member_urn: str, text: str, hashtags: list[str]) -> str:
    """Append hashtags to text and return the full post content."""
    if hashtags:
        text = text.rstrip() + "\n\n" + " ".join(hashtags)
    return text


def publish_post(access_token: str, member_urn: str, content: str) -> dict:
    """Create a LinkedIn post via the REST API."""
    url = "https://api.linkedin.com/rest/posts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202601",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": member_urn,
        "commentary": content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)

    if resp.status_code == 201:
        post_urn = resp.headers.get("x-restli-id", "")
        return {"ok": True, "post_urn": post_urn, "status_code": 201}
    else:
        return {
            "ok": False,
            "status_code": resp.status_code,
            "error": resp.text,
        }


def get_due_posts(queue: dict) -> list[dict]:
    """Return queued posts whose scheduled datetime has passed."""
    now = datetime.now()
    due = []
    for post in queue["posts"]:
        if post["status"] != "queued":
            continue
        sched_dt = datetime.strptime(
            f"{post['scheduled_date']} {post['scheduled_time']}", "%Y-%m-%d %H:%M"
        )
        if now >= sched_dt:
            due.append(post)
    return due


def show_status(queue: dict) -> None:
    """Print queue summary."""
    queued = [p for p in queue["posts"] if p["status"] == "queued"]
    posted = [p for p in queue["posts"] if p["status"] == "posted"]
    failed = [p for p in queue["posts"] if p["status"] == "failed"]

    print(f"\n{'='*60}")
    print(f"LinkedIn Queue Status -- {len(queue['posts'])} total posts")
    print(f"  Queued:  {len(queued)}")
    print(f"  Posted:  {len(posted)}")
    print(f"  Failed:  {len(failed)}")
    print(f"{'='*60}\n")

    for post in queue["posts"]:
        marker = {"queued": "[QUEUED]", "posted": "[DONE]", "failed": "[FAIL]"}.get(
            post["status"], "?"
        )
        preview = post["text"][:70].replace("\n", " ")
        date_info = post["scheduled_date"]
        extra = ""
        if post["status"] == "posted" and post.get("posted_at"):
            extra = f" (posted {post['posted_at']})"
        print(f"  {marker} {date_info} [{post['id']}] {preview}...{extra}")
    print()


def run_post(queue: dict, post: dict, dry_run: bool) -> bool:
    """Attempt to post a single queue item. Returns True on success."""
    config = queue["config"]
    content = build_post_body(config["member_urn"], post["text"], post["hashtags"])

    log.info(f"{'[DRY RUN] ' if dry_run else ''}Posting {post['id']}: {post['text'][:60]}...")

    if dry_run:
        log.info(f"  Would post {len(content)} chars to {config['member_urn']}")
        return True

    access_token = load_token(config["token_path"])
    result = publish_post(access_token, config["member_urn"], content)

    if result["ok"]:
        post["status"] = "posted"
        post["posted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        post["post_urn"] = result["post_urn"]
        log.info(f"  Posted successfully: {result['post_urn']}")
        return True
    else:
        post["status"] = "failed"
        post["error"] = result["error"][:500]
        log.error(f"  Failed ({result['status_code']}): {result['error'][:200]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Auto-Poster")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    parser.add_argument("--force", type=str, help="Force-post a specific post ID now")
    parser.add_argument("--status", action="store_true", help="Show queue status")
    args = parser.parse_args()

    queue = load_queue()

    if args.status:
        show_status(queue)
        return

    if args.force:
        target = next((p for p in queue["posts"] if p["id"] == args.force), None)
        if not target:
            log.error(f"Post ID '{args.force}' not found in queue")
            sys.exit(1)
        if target["status"] == "posted":
            log.warning(f"Post '{args.force}' already posted at {target.get('posted_at')}")
            sys.exit(1)
        target["status"] = "queued"  # reset if failed
        run_post(queue, target, args.dry_run)
        if not args.dry_run:
            save_queue(queue)
        return

    due = get_due_posts(queue)
    if not due:
        log.info("No posts due right now")
        return

    # Post only the first due item per run (avoid flooding)
    post = due[0]
    run_post(queue, post, args.dry_run)
    if not args.dry_run:
        save_queue(queue)


if __name__ == "__main__":
    main()

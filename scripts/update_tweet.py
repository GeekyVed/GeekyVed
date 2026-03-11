import sys
import re
from playwright.sync_api import sync_playwright


TARGET_USERNAME = "xgeekyved"
PROFILE_URL = f"https://x.com/{TARGET_USERNAME}"


def fetch_latest_tweet():
    """Use a headless browser to visit the public X profile and scrape the latest tweet."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        print(f"Navigating to {PROFILE_URL} ...")
        page.goto(PROFILE_URL, wait_until="networkidle", timeout=60000)

        # Wait for tweet articles to load
        print("Waiting for tweets to load ...")
        page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)

        # Get all tweet articles
        articles = page.query_selector_all('article[data-testid="tweet"]')

        if not articles:
            print("No tweet articles found on the page.")
            browser.close()
            return None, None

        # Extract text and link from the first (latest) tweet
        first_article = articles[0]

        # Get tweet text — it's inside a div with data-testid="tweetText"
        text_el = first_article.query_selector('[data-testid="tweetText"]')
        tweet_text = text_el.inner_text().strip() if text_el else ""

        # Get the tweet link — look for the timestamp link which contains the status URL
        time_link = first_article.query_selector('a[href*="/status/"] time')
        tweet_link = ""
        if time_link:
            parent_a = time_link.evaluate('el => el.parentElement.getAttribute("href")')
            if parent_a:
                tweet_link = f"https://x.com{parent_a}"

        browser.close()
        return tweet_text, tweet_link


def update_readme(tweet_text, tweet_link):
    """Inject the tweet into README.md between the markers."""
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    start_marker = "<!-- TWEET_START -->"
    end_marker = "<!-- TWEET_END -->"

    start_idx = readme.find(start_marker)
    end_idx = readme.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("Could not find TWEET_START / TWEET_END markers in README.md")
        sys.exit(1)

    link_html = ""
    if tweet_link:
        link_html = f'\n    — <a href="{tweet_link}">Read the full post on X</a>'

    injection = f"""<div align="center">
  <blockquote>
    <p><i>"{tweet_text}"</i></p>{link_html}
  </blockquote>
</div>"""

    new_readme = (
        readme[: start_idx + len(start_marker)]
        + "\n"
        + injection
        + "\n  "
        + readme[end_idx:]
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)

    print("Successfully updated README.md with the latest tweet!")


def main():
    tweet_text, tweet_link = fetch_latest_tweet()

    if not tweet_text:
        print("Could not fetch latest tweet. Exiting gracefully.")
        sys.exit(0)

    print(f"Latest tweet: {tweet_text}")
    print(f"Link: {tweet_link}")

    update_readme(tweet_text, tweet_link)


if __name__ == "__main__":
    main()

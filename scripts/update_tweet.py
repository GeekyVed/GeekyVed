import os
import sys
from playwright.sync_api import sync_playwright


TARGET_USERNAME = "xgeekyved"
PROFILE_URL = f"https://x.com/{TARGET_USERNAME}"


def login_to_x(page, username, email, password):
    """Log into X.com using the login flow."""
    print("Navigating to X login page ...")
    page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=30000)

    # Step 1: Enter username/email
    print("Entering username ...")
    # Wait for the input field to be ready
    username_locator = page.locator('input[autocomplete="username"]')
    username_locator.wait_for(state="visible", timeout=15000)
    
    # X.com's React form actively clears instantaneously filled inputs 
    # Click then type slowly to simulate human interaction
    username_locator.click()
    page.keyboard.type(username, delay=50)
    
    # Wait a moment for React state updates, then explicitly click Next
    page.wait_for_timeout(1000)
    next_btn = page.locator('button:has-text("Next")')
    next_btn.wait_for(state="visible", timeout=5000)
    next_btn.click(force=True)

    # Step 2: X might ask for email verification or go straight to password
    print("Waiting for next step ...")
    try:
        # Check if X asks for email/phone verification (suspicious login check)
        verify_locator = page.locator('input[data-testid="ocfEnterTextTextInput"]')
        verify_locator.wait_for(state="visible", timeout=5000)
        print("Email/phone verification requested, entering email ...")
        
        verify_locator.click()
        page.keyboard.type(email, delay=50)
        
        page.wait_for_timeout(1000)
        verify_next = page.locator('button:has-text("Next")')
        verify_next.wait_for(state="visible", timeout=5000)
        verify_next.click(force=True)
    except Exception:
        # No verification step — go straight to password
        print("No email verification requested.")
        pass

    # Step 3: Enter password
    print("Entering password ...")
    try:
        password_locator = page.locator('input[name="password"], input[type="password"]')
        password_locator.wait_for(state="visible", timeout=15000)
        
        password_locator.click()
        page.keyboard.type(password, delay=50)
        
        page.wait_for_timeout(1000)
        login_btn = page.locator('button:has-text("Log in")')
        login_btn.wait_for(state="visible", timeout=5000)
        login_btn.click(force=True)
    except Exception as e:
        page.screenshot(path="debug_screenshot.png")
        print(f"Failed to find password field. Saved debug_screenshot.png. Error: {e}")
        raise

    # Wait for login to complete — look for the home timeline or profile elements
    print("Waiting for login to complete ...")
    try:
        page.wait_for_selector(
            '[data-testid="primaryColumn"], [data-testid="AppTabBar_Home_Link"]',
            timeout=20000,
        )
        print("Login successful!")
    except Exception as e:
        page.screenshot(path="debug_screenshot.png")
        print(f"Login may have failed. Saved debug_screenshot.png. Error: {e}")
        raise


def fetch_latest_tweet(page):
    """Navigate to the profile and scrape the latest tweet."""
    print(f"Navigating to {PROFILE_URL} ...")
    page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=30000)

    # Wait for tweet articles to appear
    print("Waiting for tweets to load ...")
    try:
        page.wait_for_selector('article[data-testid="tweet"]', timeout=20000)
    except Exception:
        page.screenshot(path="debug_screenshot.png")
        print("Tweets did not load. Saved debug_screenshot.png")
        print(f"Page title: {page.title()}")
        return None, None

    # Get all tweet articles
    articles = page.query_selector_all('article[data-testid="tweet"]')

    if not articles:
        print("No tweet articles found on the page.")
        return None, None

    first_article = articles[0]

    # Get tweet text
    text_el = first_article.query_selector('[data-testid="tweetText"]')
    tweet_text = text_el.inner_text().strip() if text_el else ""

    # Get the tweet link
    tweet_link = ""
    time_link = first_article.query_selector('a[href*="/status/"] time')
    if time_link:
        href = time_link.evaluate('el => el.parentElement.getAttribute("href")')
        if href:
            tweet_link = f"https://x.com{href}"

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
    username = os.environ.get("X_USERNAME")
    email = os.environ.get("X_EMAIL")
    password = os.environ.get("X_PASSWORD")

    if not all([username, email, password]):
        print("Error: Missing X credentials in environment variables.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        try:
            login_to_x(page, username, email, password)
            tweet_text, tweet_link = fetch_latest_tweet(page)
        except Exception as e:
            print(f"Error: {e}")
            tweet_text, tweet_link = None, None
        finally:
            browser.close()

    if not tweet_text:
        print("Could not fetch latest tweet. Exiting gracefully.")
        sys.exit(1) # We WANT it to fail if it hits an error so you know it broke

    print(f"Latest tweet: {tweet_text}")
    print(f"Link: {tweet_link}")

    update_readme(tweet_text, tweet_link)


if __name__ == "__main__":
    main()

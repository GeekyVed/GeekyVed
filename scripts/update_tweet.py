import os
import sys
import asyncio
from twikit import Client

async def main():
    # Authentication credentials from GitHub Secrets
    username = os.environ.get('X_USERNAME')
    email = os.environ.get('X_EMAIL')
    password = os.environ.get('X_PASSWORD')

    if not all([username, email, password]):
        print("Error: Missing X credentials in environment variables.")
        sys.exit(1)

    # Initialize client
    client = Client(language='en-US')

    try:
        # Load cookies if available to avoid login loops, otherwise login
        if os.path.exists('cookies.json'):
            client.load_cookies('cookies.json')
        else:
            await client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password
            )
            client.save_cookies('cookies.json')

        # Get target user (the one we want the latest tweet from)
        target_username = 'xgeekyved'
        user = await client.get_user_by_screen_name(target_username)
        
        # Get user's tweets
        tweets = await user.get_tweets('UserTweets')
        
        if not tweets:
            print("No tweets found.")
            sys.exit(0)
            
        latest_tweet = tweets[0]
        tweet_id = latest_tweet.id
        tweet_text = latest_tweet.text
        
        # Build the HTML/Markdown payload to inject
        # Since we want it to look good and we can't use scripts, we will use a static fallback 
        # that renders the text, or we can just use the Twitter link itself.
        # But wait, Twitter cards are generated automatically by GitHub if it's just a raw link!
        # Actually, GitHub doesn't natively expand twitter links into rich cards in READMEs.
        # We will keep the banner image but link it to the specific latest tweet, 
        # OR we can inject the text of the tweet.
        
        # Let's inject a nice blockquote with the tweet text and a link!
        
        injection = f"""<div align="center">
  <blockquote>
    <p><i>"{tweet_text}"</i></p>
    — <a href="https://x.com/{target_username}/status/{tweet_id}">Read the full post on X</a>
  </blockquote>
</div>"""

        # Read the README
        with open('README.md', 'r', encoding='utf-8') as file:
            readme = file.read()
            
        # Find markers
        start_marker = "<!-- TWEET_START -->"
        end_marker = "<!-- TWEET_END -->"
        
        start_idx = readme.find(start_marker)
        end_idx = readme.find(end_marker)
        
        if start_idx != -1 and end_idx != -1:
            new_readme = readme[:start_idx + len(start_marker)] + "\n" + injection + "\n  " + readme[end_idx:]
            
            with open('README.md', 'w', encoding='utf-8') as file:
                file.write(new_readme)
            print("Successfully updated README.md with the latest tweet!")
        else:
            print("Could not find markers in README.md")
            sys.exit(1)

    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

import os
from dotenv import load_dotenv
import tweepy

load_dotenv()  # Load environment variables from .env file
api_key = os.environ.get("TWITTER_API_KEY")
api_secret = os.environ.get("TWITTER_API_KEY_SECRET")
bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

# V1 Twitter API Authentication
auth = tweepy.OAuthHandler(api_key, api_secret)
auth.set_access_token(access_token, access_secret)
api = tweepy.API(auth, wait_on_rate_limit=True)

# V2 Twitter API Authentication
client = tweepy.Client(
    bearer_token,
    api_key,
    api_secret,
    access_token,
    access_secret,
    wait_on_rate_limit=True,
)


def create_tweet(text, media_path):
    print("Uploading Tweet...")
    media_ids = []
    for media in media_path:
        media_id = api.media_upload(filename=media).media_id_string
        print("Media successfully uploaded! Id: " + media_id)
        media_ids.append(media_id)

    client.create_tweet(text=text, media_ids=media_ids)
    print("Tweeted!")

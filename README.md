# BrannTicketCounter
This python script will NOT help buy you tickets.
It's made for getting information about ticket sales
and posting it to Twitter.

# Installation
To set it up you'll have to add your own keys and tokens
if you want it to create Twitter posts.

I have it set up to automatically read and use matching keys in a .env file.
If you want to do the same, follow these steps:
- Create a ".env" file in the local folder.
- Add the following code to you .env file:
```
TWITTER_API_KEY="your_key"
TWITTER_API_KEY_SECRET="your_key"
TWITTER_BEARER_TOKEN="your_key"
TWITTER_ACCESS_TOKEN="your_key"
TWITTER_ACCESS_TOKEN_SECRET="your_key"
```
if you want to use your own solution,
you'll want to edit the twitter.py file.

# Code
The scrape_tools.py is a mess, but works
and I have added comments throughtout the code
to make it more readable.

The imagify.py file is a copy of a
[source I found on the web](https://rk.edu.pl/en/generating-memes-and-infographics-with-pillow/).
I have modified it a bit to make it fit for my use (Colors, fonts and image).

twitter.py is a basic file to let me use the Twitter 2.0 API.
Credit for the code provided goes to
[this YouTuber](https://www.youtube.com/watch?v=r9DzYE5UD6M&t=6s).
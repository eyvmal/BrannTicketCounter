# BrannTicketCounter
This Python script will **not** buy you tickets.
Instead, it gathers information about ticket sales
and posts updates to Twitter.

The program tallies available tickets for all upcoming matches.
For UEFA matches, it automatically skips all standing sections
since they're prohibited.

Calculating the number of sold tickets in the standing sections
isn't straightforward. Therefore, "Store Stå" is estimated based on
the percentage of the "Frydenbø" section's sales.
For instance, if "Frydenbø" is 50% sold out,
the script will assume 50% of "Store Stå" is sold too.

I'm still figuring out how to factor in the standing sections
for the "Fjordkraft" section.

---

# Installation and setup
To get started, you'll need to add your keys and tokens
if you're looking to post on Twitter.

I've set it to auto-detect and use keys from a .env file.
If you want to do the same, follow these steps:
- Create a .env file in your local directory.
- Pop in the code below:
```
TWITTER_API_KEY="your_key"
TWITTER_API_KEY_SECRET="your_key"
TWITTER_BEARER_TOKEN="your_key"
TWITTER_ACCESS_TOKEN="your_key"
TWITTER_ACCESS_TOKEN_SECRET="your_key"
```
If you've got your own way of doing things,
tweak the twitter.py file as needed.

---

# The Code
**scrape_tools.py** heads to the event landing page at the
"HOMEPAGE_URL" variable, sifting through the HTML for upcoming events.
It then jumps to each event's URL and scrape the HTML for the URL to
purchase tickets. From there it will get a JSON file of all the sections.
Knowing the event URL and the section IDs, it shoots a GET request to each
section to fetch all seating info. Using the seats, it calculates the amount
of sold tickets. Once that's wrapped up, it saves everything locally and
converts it to a tweet-friendly format.

---

**imagify.py** takes a String input, put it onto an image,
save it and return the image path.

The code is pretty much a copy-paste of a [source I found on the web](https://rk.edu.pl/en/generating-memes-and-infographics-with-pillow/).
I have modified it a bit to make it fit for my use (Colors, fonts and images).

---

**twitter.py** is a simple file to connect to the Twitter 2.0 API.
It will create and post Tweets having an input for the text I want
in the Tweet title and an input for the images I want to attach to the
Tweet.

Credit for the code provided goes to [this YouTuber](https://www.youtube.com/watch?v=r9DzYE5UD6M&t=6s).
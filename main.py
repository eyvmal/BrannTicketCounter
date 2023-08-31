#!/usr/bin/env python3
from imagify import generate_images
from scrape_tools import update_events
from twitter import create_tweet

# 'all', 'next', 'none' or 'debug'
strings = update_events("all")

if strings:
    images = generate_images(strings)
    tweet_header = ("Info om billettsalget for Brann sine kommende hjemmekamper!"
                    "\nEkskl. bortefelt & fjordkraft sin ståtribune."
                    "\n(Parantesen viser endring siden forrige oppdatering)")
    create_tweet(tweet_header, images)
else:
    print("No upcoming events")

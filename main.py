#!/usr/bin/env python3
from imagify import generate_images
from scrape_tools import update_events
from twitter import create_tweet


strings = update_events("all")
images = generate_images(strings)

tweet_header = ("Info om billettsalget for brann sine kommende hjemmekamper!"
                "\nEkskl. bortefelt & fjordkraft sin ståtribune."
                "\n(Parantesen viser endring siden forrige oppdatering)")

create_tweet(tweet_header, images)

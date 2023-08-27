#!/usr/bin/env python3
from scrape_tools import *
from imagify import *
from twitter import *

SAVE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/"
IMAGE_PATH = "imagify/brann_logo.jpeg"  # Path from this file

# Updates and fetches upcoming events
update_events("all")
ticket_strings = get_ticket_sales()

# Prints the ticket info onto a picture
iteration = 0
image_paths = []
for text in ticket_strings:
    image_name = "ticket_sale_result" + str(iteration) + ".jpg"

    image_object = Imagify(os.path.join(SAVE_PATH + IMAGE_PATH), text).generate()
    image_object.save(image_name, quality=90)
    iteration += 1
    image_paths.append(image_name)

# Tweets all ticket-info-pictures with custom header
tweet_header = "Info om billettsalget for brann sine kommende hjemmekamper!"
create_tweet(tweet_header, image_paths)

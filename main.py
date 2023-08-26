#!/usr/bin/env python3
from scrape_tools import *
from imagify import *
from twitter import *

# Updates all upcoming events
update_events("all")
# update_events("next")

# Retrieves the latest json file for all upcoming events
ticket_strings = get_ticket_sales()

# Prints the ticket info onto a picture
iteration = 0
image_paths = []
for text in ticket_strings:
    image_name = "ticket_sale_result" + str(iteration) + ".jpg"

    image_object = Imagify('imagify/brann_logo.jpeg', text).generate()
    image_object.save(image_name, quality=90)
    iteration += 1
    image_paths.append(image_name)

# Tweets all ticket-info-pictures with custom header
tweet_header = "Info om billettsalget for brann sine kommende hjemmekamper!"
create_tweet(tweet_header, image_paths)

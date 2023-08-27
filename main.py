#!/usr/bin/env python3
from scrape_tools import *
from imagify import *
from twitter import *

# Updates and fetches upcoming events
update_events("all")
ticket_strings = get_ticket_sales()

# Prints the ticket info onto a picture
iteration = 0
image_paths = []
for text in ticket_strings:
    header = text.split('\n')[0].lower()
    image_path = get_image(header)

    image_name = "ticket_sale_result" + str(iteration) + ".jpg"

    image_object = Imagify(os.path.join(image_path), text).generate()
    image_object.save(image_name, quality=90)
    iteration += 1
    image_paths.append(image_name)

# Tweets all ticket-info-pictures with custom header
tweet_header = ("Info om billettsalget for brann sine kommende hjemmekamper!"
                "\n(Ekskl. bortefelt & fjordkraft sin ståtribune)")
create_tweet(tweet_header, image_paths)

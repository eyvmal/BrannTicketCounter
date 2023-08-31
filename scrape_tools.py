import datetime
import re
import pytz
from bs4 import BeautifulSoup
import requests
import json
import os

HOMEPAGE_URL = "https://brann.ticketco.events/no/nb"
SAVE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/"


# The main method for updating and fetching new ticket info
def update_events(option):
    if option.lower() == "next":
        print("Starting update of the next event... ")
        event_list = get_upcoming_events("next")
    else:
        print("Starting update of all events... ")
        event_list = get_upcoming_events("all")
        # event_list = [{"title": "Conference League: SK Brann - AZ Alkmaar",
        # "time": "imorgen", "link": "https://ticketco.events/no/nb/events/328715/seating_arrangement/"}]

    path_to_tickets = []
    for event in event_list:
        if "none" in option.lower():
            path_to_tickets.append(get_directory_path(str(event["title"])))
        else:
            path_to_tickets.append(get_ticket_info(event["link"], event["title"], event["time"]))

    finalized_strings = []
    if len(path_to_tickets) == 0:
        return None

    for path in path_to_tickets:
        finalized_strings.append(create_string(path))
    return finalized_strings


# Connect to the Brann event page and get all the links for upcoming events.
# Then go through the event links and look for the actual ticket page link.
# Return event name, event date/time and ticket link for every event
def get_upcoming_events(next_or_all):
    print("Connecting to " + HOMEPAGE_URL)
    soup = BeautifulSoup(fetch_url(HOMEPAGE_URL).text, "html.parser")

    # Find the URLs for the event pages
    print("Getting events... ", end="")
    event_list = []
    event_containers = soup.find_all("div", class_="tc-events-list--details")

    for event in event_containers:
        a_element = event.find("a", class_="tc-events-list--title")
        event_title = a_element.get_text()

        if "partoutkort" not in event_title.lower() and "gavekort" not in event_title.lower():
            event_date_time = event.find("div", class_="tc-events-list--place-time").get_text(strip=True)
            event_link = get_nested_link(a_element.get("href"))

            event_list.append({
                "title": event_title,
                "time": event_date_time,
                "link": event_link
            })
    if next_or_all.lower() == "next":
        event_list = [event_list[0]]
    print("DONE")
    return event_list


# Brann have makes you click 2 links from the event overview page to come to the ticket page
# This code finds the 2nd link if you have the first one already
def get_nested_link(url):
    soup = BeautifulSoup(fetch_url(url).text, "html.parser")
    event_url = soup.find("a", id="placeOrderLink")
    return event_url.get("href")


def fetch_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)
        return None


def get_ticket_info(event_url, event_title, event_date):
    # Scrape the .json file from the event page
    json_url = event_url + "item_types.json"
    event_title = str(event_title).replace('\n', "")
    event_date = (str(event_date).replace('\n', "")
                  .replace('@', " @ "))
    print("Updating ticket information for: " + event_title)  # Debug
    json_data = fetch_url(json_url).json()

    # Get all stadium sections where tickets are sold
    sections = [section["id"] for section in json_data["item_types"][0]["sections"]]

    # Used for the console progress bar
    percentage = round((100 / len(sections)), 2)
    iteration = 1

    results = []
    print("Counting tickets: ")
    for section in sections:
        results.append(get_section_tickets(section, event_url))

        # Progress bar
        loading = "." * iteration + " [" + str(round(percentage * iteration, 1)) + "]"
        print("\r" + loading + "%", end="", flush=True)
        iteration += 1
    print("")
    # Saving only the necessary info to operate the bot to minimize amount storage
    # If you want all info, save the "results" file instead of mini_results
    mini_results = save_minimal_info(results, event_title, event_date)
    return save_new_json(event_title, mini_results)


def get_section_tickets(section, event_url):
    # Get json for this section
    json_url = event_url + "sections/" + str(section) + ".json"
    json_data = fetch_url(json_url).json()

    # Saves name, id and number of available seats remaining
    section_name = json_data["seating_arrangements"]["section_name"]
    section_total = json_data["seating_arrangements"]["section_amount"]
    section_id = section
    if "stå" in str(section_name).lower():  # Special treatment for standing sections
        sold_seats = 0
        available_seats = 0
        locked_seats = 0
        phantom_seats = 0
        seats = None
    else:
        # Seat objects
        seats = [seat for seat in json_data["seating_arrangements"]["seats"]]

        # Extract seats with status "sold"
        sold_seats = len([seat for seat in seats if seat["status"] == "sold"])

        # Extract seats with status "available"
        available_seats = len([seat for seat in seats if seat["status"] == "available"])

        # For statistics :)
        locked_seats = len([seat for seat in seats if seat["status"] == "locked"])

        # Count phantom seats and deduct them from section
        phantom_seats = len([seat for seat in seats if float(seat["x"]) <= 0 and seat["status"] == "available"])
        available_seats -= phantom_seats
        section_total -= phantom_seats

    return {
        "section_name": section_name,
        "section_id": section_id,
        "section_amount": section_total,
        "sold_seats": sold_seats,
        "available_seats": available_seats,
        "locked_seats": locked_seats,
        "phantom_seats": phantom_seats,
        "seats:": seats
    }


def save_new_json(event_title, file):
    # Get directory to save results
    dir_path = get_directory_path(event_title)
    time_now = get_time_formatted("computer")
    filename = f"results_{time_now}.json"

    # Save results to a JSON file with the formatted datetime in the specified directory
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w") as json_file:
        json.dump(file, json_file)
        print(f"File saved at {file_path}")
    return dir_path


# Checks if directory exists, if not it will create a new
def get_directory_path(event_name):
    # Remove characters that are not allowed in directory names and remove spaces
    valid_dir_name = (re.sub(r'[<>:"/\\|?*]', '', event_name)
                      .replace(' ', '')
                      .replace('\n', ''))
    dir_path = os.path.join(SAVE_PATH, valid_dir_name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


# Formats time for human eyes or sorting files on the computer
def get_time_formatted(computer_or_human):
    # Get the local time zone for Norway
    norway_timezone = pytz.timezone("Europe/Oslo")
    current_datetime = datetime.datetime.now(norway_timezone)

    if computer_or_human.lower() == "computer":  # Used to save files locally
        return str(current_datetime.strftime("%Y-%m-%d_%H-%M-%S"))
    else:  # Else for human readability
        return str(current_datetime.strftime("%H:%M %d/%m/%Y"))


def save_minimal_info(json_file, event_title, event_date):
    print("Formatting ticket info to minimal info... ", end="", flush=True)
    # Check if the event name contains a word that suggests that the game is played in europe
    # to filter out the prohibited sections from the calculations
    event_title_lower = event_title.lower()
    europa = False
    if "conference" in event_title_lower or "europa" in event_title_lower or "champions" in event_title_lower:
        europa = True  # Used in an if statement later on

    category_totals = {
        "GENERAL:": {"title": event_title, "date": event_date},
        "FRYDENBØ": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "SPV": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "BT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "FJORDKRAFT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "VIP": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "TOTALT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0}
    }
    # Remove all sections where no seats are available AND no are sold (All standing sections + away section).
    json_file = [section for section in json_file if section["sold_seats"] != 0 or section["available_seats"] != 0]

    for section in json_file:
        section_name = section["section_name"].lower()
        if "fjordkraft" in section_name and "felt b" in section_name:
            continue
        category_totals["TOTALT"]["sold_seats"] += section["sold_seats"]
        category_totals["TOTALT"]["section_amount"] += section["section_amount"]
        category_totals["TOTALT"]["available_seats"] += section["available_seats"]

    for section in json_file:
        section_name = section["section_name"].lower()
        sold_seats = section["sold_seats"]
        total_capacity = section["section_amount"]
        available_seats = section["available_seats"]

        if "spv" in section_name:
            category_totals["SPV"]["sold_seats"] += sold_seats
            category_totals["SPV"]["section_amount"] += total_capacity
            if "press" not in section_name:
                category_totals["SPV"]["available_seats"] += available_seats
            else:
                # I'm cheating the numbers because press is never actually sold
                category_totals["SPV"]["available_seats"] += 0
        elif "bob" in section_name:
            category_totals["BT"]["sold_seats"] += sold_seats
            category_totals["BT"]["section_amount"] += total_capacity
            category_totals["BT"]["available_seats"] += available_seats
        elif "frydenbø" in section_name:
            category_totals["FRYDENBØ"]["sold_seats"] += sold_seats
            category_totals["FRYDENBØ"]["section_amount"] += total_capacity
            category_totals["FRYDENBØ"]["available_seats"] += available_seats
        elif "fjordkraft" in section_name and "felt b" not in section_name:
            category_totals["FJORDKRAFT"]["sold_seats"] += sold_seats
            category_totals["FJORDKRAFT"]["section_amount"] += total_capacity
            category_totals["FJORDKRAFT"]["available_seats"] += available_seats
        elif "vip" in section_name:
            category_totals["VIP"]["sold_seats"] += sold_seats
            category_totals["VIP"]["section_amount"] += total_capacity
            category_totals["VIP"]["available_seats"] += available_seats

    # Add an estimate for Store Stå to the Frydenbø section
    if europa is False:
        percentage = round((category_totals["FRYDENBØ"]["sold_seats"] / category_totals["FRYDENBØ"]["section_amount"]),
                           2)
        category_totals["FRYDENBØ"]["sold_seats"] += round(1200 * percentage)
        category_totals["FRYDENBØ"]["section_amount"] += 1200
        category_totals["TOTALT"]["sold_seats"] += round(1200 * percentage)
        category_totals["TOTALT"]["section_amount"] += 1200
    print("DONE")
    return category_totals


# Returns the two most recently edited files.
def get_latest_file(dir_path):
    files = os.listdir(dir_path)
    sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(dir_path, x)), reverse=True)
    if len(sorted_files) > 1:
        latest_file_path = os.path.join(dir_path, sorted_files[0])
        prior_file_path = os.path.join(dir_path, sorted_files[1])
        with open(latest_file_path, "r") as json_file:
            latest_file = json.load(json_file)
        with open(prior_file_path, "r") as json_file:
            prior_file = json.load(json_file)
        return latest_file, prior_file
    else:
        latest_file_path = os.path.join(dir_path, sorted_files[0])
        with open(latest_file_path, "r") as json_file:
            return json.load(json_file), None


def create_string(file_path):
    latest, prior = get_latest_file(file_path)
    return_value = ""

    # c is category and d is data. Result is a dictionary containing c and d
    for c, d in latest.items():
        if "GENERAL" in c:
            return_value = d["title"] + "\n" + d["date"] + "\n\n"
            continue

        # sold_seats = d['sold_seats']
        available_seats = d["available_seats"]
        total_capacity = d["section_amount"]
        sold_seats = total_capacity - available_seats
        percentage_sold = (sold_seats / total_capacity) * 100 if total_capacity != 0 else 0

        # Newline before the total to separate it from the rest of the results
        if c.lower() == "totalt":
            return_value += "\n"

        if prior is not None:
            prior_available_seats = prior[c]["available_seats"]
            prior_sold_seats = total_capacity - prior_available_seats
            prior_percentage_sold = (prior_sold_seats / total_capacity) * 100 if total_capacity != 0 else 0
            diff_percentage = percentage_sold - prior_percentage_sold
            return_value += f"{c.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)}" \
                            f"{f'{percentage_sold:.1f}%'.ljust(6)} ({diff_percentage:+.1f}%)\n"
        else:
            return_value += f"{c.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)} {percentage_sold:.1f}%\n"
    time_now = get_time_formatted("human")
    return_value += f"\n\nOppdatert: {time_now}\n "
    return return_value

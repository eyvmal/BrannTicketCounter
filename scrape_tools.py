import datetime
import re
import pytz
from bs4 import BeautifulSoup
import requests
import json
import os

HOMEPAGE_URL = "https://brann.ticketco.events/no/nb"
SAVE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/"


def get_directory(event_name):
    # Remove characters that are not allowed in directory names and remove spaces
    valid_dir_name = re.sub(r'[<>:"/\\|?*]', '', event_name).replace(' ', '')
    valid_dir_name = os.path.join(SAVE_PATH, valid_dir_name)

    if not os.path.exists(valid_dir_name):
        os.makedirs(valid_dir_name)
    return valid_dir_name


def get_time_formatted(computer_or_human):
    # Get the local time zone for Norway
    norway_timezone = pytz.timezone("Europe/Oslo")
    current_datetime = datetime.datetime.now(norway_timezone)

    if computer_or_human.lower() == "computer":  # Used to save files locally
        return str(current_datetime.strftime("%Y-%m-%d_%H-%M-%S"))
    else:  # Else for human readability
        return str(current_datetime.strftime("%H:%M %d/%m/%Y"))


def fetch_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)
        return None


def get_ticket_info(event_url, event_name):
    # Scrape the .json file from the event page
    json_url = event_url + "item_types.json"
    print("Updating ticket information for: " + event_name)  # Debug
    response = fetch_url(json_url)
    json_data = response.json()

    # Get all stadium sections where tickets are sold
    sections = [section["id"] for section in json_data["item_types"][0]["sections"]]
    results = []

    # Progress bar
    percentage = round((100 / len(sections)), 2)
    iteration = 1

    print("Counting tickets: ")
    for section in sections:
        # Get json for this section
        json_url = event_url + "sections/" + str(section) + ".json"
        response = fetch_url(json_url)
        json_data = response.json()

        # Saves name, id and number of available seats remaining
        section_name = json_data["seating_arrangements"]["section_name"]
        section_amount = json_data["seating_arrangements"]["section_amount"]
        section_id = section
        if "STÅ" in section_name:  # Special treatment for standing sections
            # Have to check later if this changes when the section is sold out or not
            # status = json_data["seating_arrangements"]["areas"][0]["status"]
            # print("\nDEBUG: " + str(section_name) + ", status: " + str(status))
            num_sold_seats = 0
            num_available_seats = 0
        else:
            # Extract seats with status "sold"
            sold_seats = [seat for seat in json_data["seating_arrangements"]["seats"] if
                          seat["status"] == "sold"]
            num_sold_seats = len(sold_seats)

            # Extract seats with status "available"
            available_seats = [seat for seat in json_data["seating_arrangements"]["seats"] if
                               seat["status"] == "available"]
            num_available_seats = len(available_seats)

        # Save section info as dictionary
        section_info = {
            "section_name": section_name,
            "section_id": section_id,
            "section_amount": section_amount,
            "sold_seats": num_sold_seats,
            "available_seats": num_available_seats
        }

        # Append the section_info to results
        results.append(section_info)

        # Console output
        loading = "." * iteration + " [" + str(round(percentage * iteration, 1)) + "]"
        print("\r" + loading + "%", end="", flush=True)
        iteration += 1

    print("")  # debug
    # Get directory to save results
    dir_path = get_directory(event_name)
    time_now = get_time_formatted("computer")
    filename = f"results_{time_now}.json"

    # Save results to a JSON file with the formatted datetime in the specified directory
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w") as json_file:
        json.dump(results, json_file)

    print(f"File saved as: {filename} in directory: {dir_path}/\n")


def get_event_info(url, next_or_all):
    # Get HTML
    print("Fetching " + url)
    response = fetch_url(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the URLs for the event pages
    print("Looking for events... ", end="")
    title_a_tags = soup.find_all("a", class_="tc-events-list--title")
    href_values = [a.get("href") for a in title_a_tags]

    # Remove seasoncard and giftcard link
    filtered_href_values = [href for href in href_values if "partoutkort" not in href and "gavekort" not in href]

    event_info = []
    if next_or_all.lower() == "next":
        filtered_href_values = [filtered_href_values[0]]

    for url in filtered_href_values:
        response = fetch_url(url)
        soup = BeautifulSoup(response.text, "html.parser")

        event_name = soup.find("h1", class_="page-title")
        event_url = soup.find("a", id="placeOrderLink")

        if event_url and event_name:
            event_info.append({"event_url": event_url.get("href"), "event_name": event_name.get_text()})
    print("DONE")
    print()
    return event_info


def update_events(next_or_all):
    print("Starting update of all ticket sales... ")
    event_info = []
    if next_or_all.lower() == "next":
        event_info = get_event_info(HOMEPAGE_URL, "next")
    elif next_or_all.lower() == "all":
        event_info = get_event_info(HOMEPAGE_URL, "all")
    else:
        print("ERROR: update_events() couldn't run properly as input was neither 'next' or 'all'")

    for event in event_info:
        get_ticket_info(event["event_url"], event["event_name"])


def get_latest_file(dir_path):
    files = os.listdir(dir_path)
    sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(dir_path, x)), reverse=True)
    file_path = os.path.join(dir_path, sorted_files[0])

    with open(file_path, "r") as json_file:
        return json.load(json_file)


def get_tickets(json_file, event_name):
    event_name_lower = event_name.lower()

    # Check if the event name contains a word that suggests that the game is played in europe
    # to filter out the prohibited sections from the calculations
    europa = False
    if "conference" in event_name_lower or "europa" in event_name_lower or "champions" in event_name_lower:
        europa = True  # Used in an if statement later on

    category_totals = {
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
        sold_seats = section["sold_seats"]
        total_capacity = section["section_amount"]
        available_seats = section["available_seats"]
        category_totals["TOTALT"]["sold_seats"] += sold_seats
        category_totals["TOTALT"]["section_amount"] += total_capacity
        category_totals["TOTALT"]["available_seats"] += available_seats

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
        elif "fjordkraft" in section_name:
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
    return category_totals


def get_ticket_sales():
    event_info = get_event_info(HOMEPAGE_URL, "all")
    results = []

    for event in event_info:
        json_file = get_latest_file(get_directory(event["event_name"]))
        result = get_tickets(json_file, event["event_name"])

        return_value = "\n" + event["event_name"] + "\n\n"

        for c, d in result.items():
            # sold_seats = d['sold_seats']
            available_seats = d["available_seats"]
            total_capacity = d["section_amount"]
            sold_seats = total_capacity - available_seats
            percentage_sold = (sold_seats / total_capacity) * 100 if total_capacity != 0 else 0

            # Make the total stand out of the rest of the numbers
            if c.lower() == "totalt":
                return_value += "\n"

            return_value += f"{c.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(11)} ({percentage_sold:.1f}%)\n"
        time_now = get_time_formatted("human")
        return_value += f"\n\nOppdatert: {time_now}\n"
        results.append(return_value)

    return results

import datetime
import re
import pytz
import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HOMEPAGE_URL = "https://brann.ticketco.events/no/nb"
SAVE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/"

session = requests.Session()
# Prevents requests from looping forever
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)


def update_events(option):
    """
        The initiating method for the script.
    :param option:
        This will either update 'all' event, the 'next' event,
        'none' of the events (just print what information is already saved locally),
        or save a 'debug' (all seat information about all events)
    :return:
       String output containing ticket information about the event(s).
    """
    valid_options = ["all", "next", "none", "debug"]
    if option.lower() not in valid_options:
        raise ValueError(f"Invalid option: {option}. Valid options are: {', '.join(valid_options)}")

    if option.lower() == "next" or option.lower() == "debug":
        print("Starting update of the next event... ")
        event_list = get_upcoming_events("next")
    else:
        print("Starting update of all events... ")
        event_list = get_upcoming_events("all")

    dir_path_to_tickets = []
    for event in event_list:
        print("")
        if "none" in option.lower():
            dir_path_to_tickets.append(get_directory_path(str(event["title"])))
        elif "debug" in option.lower():
            dir_path_to_tickets.append(get_ticket_info(event["link"], event["title"], event["time"], True))
            print("Debug done.")
            return None
        else:
            dir_path_to_tickets.append(get_ticket_info(event["link"], event["title"], event["time"], False))
    print("")
    finalized_strings = []
    if len(dir_path_to_tickets) == 0:
        return None

    for path in dir_path_to_tickets:
        finalized_strings.append(create_string(path))
    return finalized_strings


def get_upcoming_events(next_or_all):
    """
    Connects to the Brann main event page to collect the URLs for all upcoming events.
    :param next_or_all:
        Decides if this method will return all upcoming events or just the next
    :return:
        A list of the next or all upcoming events
    """
    print("Connecting to " + HOMEPAGE_URL)
    soup = BeautifulSoup(fetch_url(HOMEPAGE_URL).text, "html.parser")

    print("Getting events... ", end="")
    event_list = []
    try:
        event_containers = soup.find_all("div", class_="tc-events-list--details")
    except AttributeError:
        print("Failed to find events: The website structure may have changed.")
        return []

    for event in event_containers:
        a_element = event.find("a", class_="tc-events-list--title")
        event_title = a_element.get_text()

        # Only process the actual matches (Strips the array for gift cards, package deals etc.)
        if "brann -" in event_title.lower():
            try:
                event_date_time = event.find("div", class_="tc-events-list--place-time").get_text(strip=True)
                event_link = get_nested_link(a_element.get("href"))
                event_list.append({
                    "title": event_title,
                    "time": event_date_time,
                    "link": event_link
                })
            except AttributeError:
                print("Failed to find links in event: The website structure may have changed.")

    if next_or_all.lower() == "next":
        event_list = [event_list[0]]
    print(f"DONE")
    return event_list


def get_nested_link(url):
    """
    The Brann event provide a URL to all upcoming events.
    But to get the actual ticket information you have to get another URL.
    This method will find the URL to the ticket webpage on an event page.
    :param url:
        URL to an event page
    :return:
        returns the ticket page URL
    """
    soup = BeautifulSoup(fetch_url(url).text, "html.parser")
    event_url = soup.find("a", id="placeOrderLink")
    return event_url.get("href")


def fetch_url(url):
    """
    Gets the HTML code for a webpage
    :param url:
        URL to the webpage you want to scrape
    :return:
        HTML code for the webpage
    """
    try:
        response = session.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)
        return None


def get_ticket_info(event_url, event_title, event_date, debug):
    """
    Find all the section IDs for the event and calls a function to sort the seat information.
    Then strips the information to the bare minimum necessary, saves it, and returns the file path.
    :param event_url:
        The URL for the event you want the ticket information on
    :param event_title:
        Title of the event
    :param event_date:
        Date of the event
    :param debug:
        A boolean value to check if you want to save a debug version of the results or not
    :return:
        Directory path to where the results are saved
    """
    json_url = event_url + "item_types.json"
    event_title = str(event_title).replace('\n', "")
    event_date = (str(event_date).replace('\n', "")
                  .replace('@', " @ "))
    print("Updating ticket information for: " + event_title)
    json_data = fetch_url(json_url).json()

    sections = [section["id"] for section in json_data["item_types"][0]["sections"]]
    progress_bar = tqdm(total=len(sections), desc="Counting sections", unit="section")

    with ThreadPoolExecutor() as executor:
        ticket_info = [executor.submit(get_section_tickets, section, event_url, progress_bar) for section in sections]
    results = [info.result() for info in ticket_info]

    progress_bar.close()

    mini_results = save_minimal_info(results, event_title, event_date)
    if debug:
        return save_new_json("debug", results)
    return save_new_json(event_title, mini_results)


def get_section_tickets(section, event_url, progressbar):
    """
    Using section ID and event URL, this method will fetch a json containing all seat
    information for this section. It will then group it together for readability and return it.
    Standing sections contain no seat information, and needs special treatment.
    Sometimes seats have a weird coordinate (e.g <0) and is considered a phantom seat as it cannot be bought.
    :param section:
        Arena section ID where it will fetch ticket information
    :param event_url:
        URL to the event
    :param progressbar:
        Progress element, to update the progressbar
    :return:
        Dictionary containing grouped stats of all seats in this section
    """
    json_url = event_url + "sections/" + str(section) + ".json"
    try:
        json_data = fetch_url(json_url).json()
    except (json.JSONDecodeError, AttributeError):
        print(f"Failed to decode JSON from URL: {json_url}")
        return None

    section_name = json_data["seating_arrangements"]["section_name"]
    section_total = json_data["seating_arrangements"]["section_amount"]
    section_id = section
    if "stå" in str(section_name).lower():
        sold_seats = 0
        available_seats = 0
        locked_seats = 0
        phantom_seats = 0
        available_seats_object = None
    else:
        seats = [seat for seat in json_data["seating_arrangements"]["seats"]]
        sold_seats = len([seat for seat in seats if seat["status"] == "sold"])
        available_seats_object = [seat for seat in seats if seat["status"] == "available"]
        available_seats = len(available_seats_object)
        locked_seats = len([seat for seat in seats if seat["status"] == "locked"])
        phantom_seats = len([seat for seat in seats if float(seat["x"]) <= 0 and seat["status"] == "available"])
        available_seats -= phantom_seats
        section_total -= phantom_seats
    progressbar.update(1)
    return {
        "section_name": section_name,
        "section_id": section_id,
        "section_amount": section_total,
        "sold_seats": sold_seats,
        "available_seats": available_seats,
        "locked_seats": locked_seats,
        "phantom_seats": phantom_seats,
        "seats:": available_seats_object
    }


def save_new_json(event_title, data):
    """
    Saves data to JSON file
    :param event_title:
        Title of the event, used as directory name
    :param data:
        The data that is going to be saved to JSON
    :return:
        Returns the directory path
    """
    dir_path = get_directory_path(event_title)
    time_now = get_time_formatted("computer")
    filename = f"results_{time_now}.json"

    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w") as json_file:
        json.dump(data, json_file)
        print(f"File saved at {file_path}")
    return dir_path


def get_directory_path(event_name):
    """
    Strips the even_name for illegal characters and checks an if there already is
    a directory for a specific event. If not, a new one will be created.
    :param event_name:
        Name of the event
    :return:
        Returns path to the directory
    """
    valid_dir_name = (re.sub(r'[<>:"/\\|?*]', '', event_name)
                      .replace(' ', '')
                      .replace('\n', ''))
    dir_path = os.path.join(SAVE_PATH, valid_dir_name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def get_time_formatted(computer_or_human):
    """
    Formats time to either easily sort files chronologically (computer)
    or to easily be read by humans using local norwegian timezone and formatting.
    :param computer_or_human:
        Input telling what type of format you want.
    :return:
        Returns a string value of the time in the selected formatting.
    """
    norway_timezone = pytz.timezone("Europe/Oslo")
    current_datetime = datetime.datetime.now(norway_timezone)

    if computer_or_human.lower() == "computer":
        return str(current_datetime.strftime("%Y-%m-%d_%H-%M-%S"))
    else:
        return str(current_datetime.strftime("%H:%M %d/%m/%Y"))


def save_minimal_info(data, event_title, event_date):
    """
    Takes information about all the sections for an event and groups them together to their respective
    stands around the arena: "Frydenbø", "Sparebanken Vest", "BT", "Fjordkraft", "VIP". And add an extra
    section for the whole arena: "Total".
    - If the game is a european game, all standing sections are closed due to UEFA rules.
    - Some sections are locked and not available to the public (No seats available and no seats sold).
    - The section for media ("press") is never actually sold.
    - An estimate is added for the famous Frydenbø standing section ("Store Stå").
      Its calculated based on percentage sold of "Frydenbø".
    :param data:
        An array containing data for all the arena sections
    :param event_title:
        The title of the event
    :param event_date:
        The date of the event
    :return:
        Return a dictionary of all the sections and info about their seats
    """
    event_title_lower = event_title.lower()
    europa = False
    if "conference" in event_title_lower or "europa" in event_title_lower or "champions" in event_title_lower:
        europa = True

    category_totals = {
        "GENERAL:": {"title": event_title, "date": event_date},
        "FRYDENBØ": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "SPV": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "BT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "FJORDKRAFT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "VIP": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "TOTALT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0}
    }
    json_file = [section for section in data if section["sold_seats"] != 0 or section["available_seats"] != 0]

    for section in json_file:
        section_name = section["section_name"].lower()
        if "fjordkraft" in section_name and "felt b" in section_name or "stå" in section_name:
            continue
        category_totals["TOTALT"]["sold_seats"] += section["sold_seats"]
        category_totals["TOTALT"]["section_amount"] += section["section_amount"]
        if "press" not in section_name:
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
        elif "bob" in section_name:
            category_totals["BT"]["sold_seats"] += sold_seats
            category_totals["BT"]["section_amount"] += total_capacity
            category_totals["BT"]["available_seats"] += available_seats
        elif "frydenbø" in section_name:
            category_totals["FRYDENBØ"]["sold_seats"] += sold_seats
            category_totals["FRYDENBØ"]["section_amount"] += total_capacity
            category_totals["FRYDENBØ"]["available_seats"] += available_seats
        elif "fjordkraft" in section_name and "felt b" not in section_name and "stå" not in section_name:
            category_totals["FJORDKRAFT"]["sold_seats"] += sold_seats
            category_totals["FJORDKRAFT"]["section_amount"] += total_capacity
            category_totals["FJORDKRAFT"]["available_seats"] += available_seats
        elif "vip" in section_name:
            category_totals["VIP"]["sold_seats"] += sold_seats
            category_totals["VIP"]["section_amount"] += total_capacity
            category_totals["VIP"]["available_seats"] += available_seats

    if europa is False:
        percentage = round((category_totals["FRYDENBØ"]["sold_seats"] / category_totals["FRYDENBØ"]["section_amount"]), 2)
        sold_seats = round(1200 * percentage)
        category_totals["FRYDENBØ"]["sold_seats"] += sold_seats
        category_totals["FRYDENBØ"]["section_amount"] += 1200
        category_totals["FRYDENBØ"]["available_seats"] += 1200 - sold_seats
        category_totals["TOTALT"]["sold_seats"] += sold_seats
        category_totals["TOTALT"]["section_amount"] += 1200
        category_totals["TOTALT"]["available_seats"] += 1200 - sold_seats
    return category_totals


def get_latest_file(dir_path):
    """
    Fetches the two most recently edited files (Should be the 2 most recent) in a directory.
    :param dir_path:
        Path to the directory
    :return:
        Returns the data for the respective files
    """
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


def create_string(dir_path):
    """
    Converts the data to a String, ready to be put in a Tweet.
    Also compares the two latest results to calculates the difference in tickets sold.
    :param dir_path:
        path to the event directory
    :return:
        Returns a string value of the ticket information
    """
    latest, prior = get_latest_file(dir_path)
    return_value = ""

    for category, data in latest.items():
        if "GENERAL" in category:
            return_value = data["title"] + "\n" + data["date"] + "\n\n"
            continue

        available_seats = data["available_seats"]
        total_capacity = data["section_amount"]
        sold_seats = total_capacity - available_seats
        percentage_sold = (sold_seats / total_capacity) * 100 if total_capacity != 0 else 0

        if category.lower() == "totalt":  # Adds newline before the totals
            return_value += "\n"

        if prior is not None:
            prior_available_seats = prior[category]["available_seats"]
            prior_sold_seats = total_capacity - prior_available_seats

            diff_sold_seats = sold_seats - prior_sold_seats
            if diff_sold_seats == 0:
                return_value += f"{category.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)}" \
                                f"{f''.ljust(7)} {percentage_sold:.1f}%\n"
            else:
                return_value += f"{category.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)}" \
                            f"{f'{diff_sold_seats:+}'.ljust(7)} {percentage_sold:.1f}%\n"

        else:
            return_value += f"{category.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)} {percentage_sold:.1f}%\n"
    time_now = get_time_formatted("human")
    return_value += f"\n\nOppdatert: {time_now}\n "
    return return_value

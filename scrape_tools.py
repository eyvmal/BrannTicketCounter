from datetime import datetime
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
from typing import List, Dict, Union, Tuple, Optional

HOMEPAGE_URL = "https://brann.ticketco.events/no/nb"
SAVE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/"
CUSTOM_EVENTS = [
    # {
    #         "title": "Brann - Lyon",
    #         "time": "21.12.2023 18:45@Åsane Arena",
    #         "link": "https://ticketco.events/no/nb/events/382876/seating_arrangement/"
    # },
]

session = requests.Session()
# Prevents requests from looping forever
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)


def update_events(option: str) -> Optional[List[str]]:
    """Initiates the process to update events based on the specified option.

    This function serves as the starting point for the script, initiating the process
    to scrape and update event data based on the option specified. It controls the
    behavior of the script and determines which events will be targeted for data
    retrieval and updating.
    Args:
        option (str):
            Specifies the events to target for updating. Valid values are:
            - 'all': Update data for all events.
            - 'next': Update data for the next event only.
            - 'none': Do not update any event data; only print existing data.
            - 'debug': Save detailed seat information for all events.
    Returns:
        Optional[List[str]]:
            A list of strings, each containing ticket information about the targeted event(s),
            formatted and ready for output. In 'debug' mode, no list is returned.
    """
    valid_options = ["all", "next", "none", "debug"]
    if option.lower() not in valid_options:
        raise ValueError(f"Invalid option: {option}. Valid options are: {', '.join(valid_options)}")
    else:
        print("Starting update of the next event... ")
        if option.lower() == "next":
            event_list = get_upcoming_events("next")
        else:
            event_list = get_upcoming_events("all")

    dir_path_to_tickets = []
    for event in event_list:
        if "none" in option.lower():
            dir_path_to_tickets.append(get_directory_path(str(event["title"])))
        elif "debug" in option.lower():
            dir_path_to_tickets.append(get_ticket_info(event["link"], event["title"], event["time"], True))
        else:
            dir_path_to_tickets.append(get_ticket_info(event["link"], event["title"], event["time"], False))
    print("")

    finalized_strings = []
    if len(dir_path_to_tickets) == 0 or "debug" in option.lower():
        return None

    for path in dir_path_to_tickets:
        if "utsolgt" in path.lower():
            finalized_strings.append(create_soldout_string(path))
        elif "partoutkort" in path.lower():
            finalized_strings.append(create_seasonpass_string(path))
        else:
            finalized_strings.append(create_string(path))
    return finalized_strings


def get_upcoming_events(next_or_all: str) -> List[Dict]:
    """Fetch URLs of all upcoming events from the Brann main event page.
    Args:
        next_or_all (str):
            Determines whether to return all upcoming events or just the next one.
            Accepts values: 'next', 'all'.
    Returns:
        List[Dict]:
            A list of dictionaries containing details of the next or all upcoming events.
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
        event_title = a_element.get_text(strip=True)

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
                print(f"\nFailed to find links for '${event_title}': The website structure may have changed.")

    # Add custom events if any
    for custom_event in CUSTOM_EVENTS:
        event_list.append({
            "title": custom_event["title"],
            "time": custom_event["time"],
            "link": custom_event["link"]
        })

    if next_or_all.lower() == "next":
        event_list = [event_list[0]]
    print(f"DONE")
    return event_list


def get_nested_link(url: str) -> str:
    """Find and return the ticket page URL from an event page.
    Args:
        url (str):
            The URL of the event page.
    Returns:
        str:
            The URL of the ticket page.
    """
    soup = BeautifulSoup(fetch_url(url).text, "html.parser")
    event_url = soup.find("a", id="placeOrderLink")
    return event_url.get("href")


def fetch_url(url: str) -> Optional[requests.Response]:
    """Fetch the HTML code for a webpage.
    Args:
        url (str):
            The URL of the webpage to scrape.
    Returns:
        Optional[requests.Response]:
            The HTML code of the webpage, or None if an error occurs.
    """
    try:
        response = session.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print("An error occurred:", e)
        return None


def get_ticket_info(event_url: str, event_title: str, event_date: str, debug: bool) -> str:
    """Gather and save ticket information for a given event.
    Args:
        event_url (str):
            The URL to find ticket information for the event.
        event_title (str):
            The title of the event.
        event_date (str):
            The date of the event.
        debug (bool):
            Whether to save a debug version of the results.
    Returns:
        str:
            The directory path where the results are saved.
    """
    json_url = event_url + "item_types.json"
    event_title = str(event_title).replace('\n', "")
    event_date = (str(event_date).replace('\n', "")
                  .replace('@', " @ "))
    print("\nUpdating ticket information for: " + event_title)
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


def get_section_tickets(section: int, event_url: str, progressbar) -> Optional[Dict]:
    """Fetch and organize seat information for a specific section of the arena.
    Args:
        section (int):
            The ID of the arena section to fetch ticket information for.
        event_url (str):
            The URL of the event.
        progressbar:
            The progress bar object to update during execution.
    Returns:
        Optional[Dict]:
            A dictionary containing organized stats and details of all seats in the section.
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


def save_new_json(event_title: str, data: Union[Dict, List[Dict]]) -> str:
    """Save data to a JSON file.
    Args:
        event_title (str):
            The title of the event, used as the directory name.
        data (List[Dict[str, Union[str, int]]]):
            The data to save to the JSON file.
    Returns:
        str:
            The directory path where the file is saved.
    """
    dir_path = get_directory_path(event_title)
    time_now = get_time_formatted("computer")
    filename = f"results_{time_now}.json"

    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w") as json_file:
        json.dump(data, json_file)
        print(f"File saved at {file_path}")
    return dir_path


def get_directory_path(event_name: str) -> str:
    """Creates or retrieves the directory path for a specific event.

    This function cleans the event name of illegal characters and checks if a directory
    for the specific event already exists. If it doesn't, a new directory is created.
    Args:
        event_name (str):
            The name of the event.
    Returns:
        str:
            The path to the directory corresponding to the event name.
    """
    valid_dir_name = (re.sub(r'[<>:"/\\|?*]', '', event_name)
                      .replace(' ', '')
                      .replace('\n', ''))
    dir_path = os.path.join(SAVE_PATH, valid_dir_name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def get_time_formatted(computer_or_human: str) -> str:
    """Formats the current time in a specified format.

    This function returns the current time formatted either for easy chronological file sorting
    ('computer' option) or in a human-readable format with Norwegian timezone and formatting
    ('human' option).
    Args:
        computer_or_human (str):
            The format specification, accepts 'computer' or 'human'.
    Returns:
        str:
            The formatted current time as a string.
    """
    norway_timezone = pytz.timezone("Europe/Oslo")
    current_datetime = datetime.now(norway_timezone)

    if computer_or_human.lower() == "computer":
        return str(current_datetime.strftime("%Y-%m-%d_%H-%M-%S"))
    else:
        return str(current_datetime.strftime("%H:%M %d/%m/%Y"))


def save_minimal_info(data: List[Dict], event_title: str, event_date: str) -> Dict:
    """Aggregates section data for an event.

    The function groups section data by stands around the arena, and adds a 'Total' section that
    summarizes all sections. Special rules apply for European games and certain sections like the
    press section and the Frydenbø standing section.
    Args:
        data (List[Dict[str, Union[str, int, float]]]):
            List of dictionaries containing section data for the event.
        event_title (str):
            The title of the event.
        event_date (str):
            The date of the event.
    Returns:
        Dict:
            A dictionary containing aggregated data for each category and the total.
    """
    event_title_lower = event_title.lower()
    europa = False
    if "conference" in event_title_lower or "europa" in event_title_lower or "champions" in event_title_lower:
        # Looks like women matches still allow standing sections ... ??
        if "women" not in event_title_lower and "kvinne" not in event_title_lower:
            europa = True

    venue = get_venue_from_event_date(event_date)

    if venue == "Brann Stadion":
        return brann_stadion(data, event_title, event_date, europa)
    elif venue == "Åsane Arena":
        return aasane_arena(data, event_title, event_date)


def brann_stadion(data: List[Dict], event_title: str, event_date: str, europa: bool) -> Dict:
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
        if (("fjordkraft" in section_name and (
                "felt a" in section_name or "felt b" in section_name or "stå" in section_name))
                or "gangen" in section_name or "press" in section_name):
            continue
        category_totals["TOTALT"]["sold_seats"] += section["sold_seats"]
        category_totals["TOTALT"]["section_amount"] += section["section_amount"]
        category_totals["TOTALT"]["available_seats"] += section["available_seats"]

    for section in json_file:
        section_name = section["section_name"].lower()
        sold_seats = section["sold_seats"]
        total_capacity = section["section_amount"]
        available_seats = section["available_seats"]

        if "spv" in section_name and "press" not in section_name:
            category_totals["SPV"]["sold_seats"] += sold_seats
            category_totals["SPV"]["section_amount"] += total_capacity
            category_totals["SPV"]["available_seats"] += available_seats
        elif "bob" in section_name or "bt" in section_name:
            category_totals["BT"]["sold_seats"] += sold_seats
            category_totals["BT"]["section_amount"] += total_capacity
            category_totals["BT"]["available_seats"] += available_seats
        elif "frydenbø" in section_name and "gangen" not in section_name:
            category_totals["FRYDENBØ"]["sold_seats"] += sold_seats
            category_totals["FRYDENBØ"]["section_amount"] += total_capacity
            category_totals["FRYDENBØ"]["available_seats"] += available_seats
        elif "fjordkraft" in section_name and (
                "felt a" in section_name or "felt b" in section_name or "stå" in section_name):
            category_totals["FJORDKRAFT"]["sold_seats"] += sold_seats
            category_totals["FJORDKRAFT"]["section_amount"] += total_capacity
            category_totals["FJORDKRAFT"]["available_seats"] += available_seats
        elif "vip" in section_name:
            category_totals["VIP"]["sold_seats"] += sold_seats
            category_totals["VIP"]["section_amount"] += total_capacity
            category_totals["VIP"]["available_seats"] += available_seats

    if europa is False and category_totals["FRYDENBØ"]["section_amount"] > 0:
        percentage = round((category_totals["FRYDENBØ"]["sold_seats"] /
                            category_totals["FRYDENBØ"]["section_amount"]), 2)

        sold_seats = round(1000 * percentage)
        category_totals["FRYDENBØ"]["sold_seats"] += sold_seats
        category_totals["FRYDENBØ"]["section_amount"] += 1000
        category_totals["FRYDENBØ"]["available_seats"] += 1000 - sold_seats
        category_totals["TOTALT"]["sold_seats"] += sold_seats
        category_totals["TOTALT"]["section_amount"] += 1000
        category_totals["TOTALT"]["available_seats"] += 1000 - sold_seats
    return category_totals


def aasane_arena(data: List[Dict], event_title: str, event_date: str) -> Dict:
    category_totals = {
        "GENERAL:": {"title": event_title, "date": event_date},
        "HOVED": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "FAMILIE": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "NORDRE": {"sold_seats": 0, "section_amount": 0, "available_seats": 0},
        "TOTALT": {"sold_seats": 0, "section_amount": 0, "available_seats": 0}
    }
    json_file = [section for section in data]

    for section in json_file:
        # Add totals
        category_totals["TOTALT"]["sold_seats"] += section["sold_seats"]
        category_totals["TOTALT"]["section_amount"] += section["section_amount"]
        category_totals["TOTALT"]["available_seats"] += section["available_seats"]

        section_name = section["section_name"].lower()
        sold_seats = section["sold_seats"]
        total_capacity = section["section_amount"]
        available_seats = section["available_seats"]

        if "hovedtribune" in section_name:
            category_totals["HOVED"]["sold_seats"] += sold_seats
            category_totals["HOVED"]["section_amount"] += total_capacity
            category_totals["HOVED"]["available_seats"] += available_seats
        elif "familietribune" in section_name:
            category_totals["FAMILIE"]["sold_seats"] += sold_seats
            category_totals["FAMILIE"]["section_amount"] += total_capacity
            category_totals["FAMILIE"]["available_seats"] += available_seats
        elif "nordre" in section_name:
            category_totals["NORDRE"]["sold_seats"] += sold_seats
            category_totals["NORDRE"]["section_amount"] += total_capacity
            category_totals["NORDRE"]["available_seats"] += available_seats
    return category_totals


def get_venue_from_event_date(event_date: str) -> str:
    """Extracts the venue from the event date string."""
    venue_start_index = event_date.find("@") + 1
    venue = event_date[venue_start_index:].strip()
    return venue


def get_latest_file(dir_path: str) -> Tuple[Dict, Optional[Dict]]:
    """Fetches the two most recent files in a directory.

    The function returns the data of the two most recently edited files in a directory.
    If there is only one file, the second element in the tuple will be None.
    Args:
        dir_path (str):
            The path to the directory.
    Returns:
        Tuple[Dict, Optional[Dict]]:
            The most recent and the second most recent file data, if available.
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


def create_string(dir_path: str) -> str:
    """Creates a formatted string with ticket information for a tweet.

    The function generates a string with ticket information, including differences in ticket sales
    compared to the previous data point, ready to be posted as a tweet.
    Args:
        dir_path (str):
            The path to the event directory.
    Returns:
        str:
            A string containing the formatted ticket information.
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
            prior_total_capacity = prior[category]["section_amount"]
            prior_sold_seats = prior_total_capacity - prior_available_seats

            diff_sold_seats = sold_seats - prior_sold_seats
            if diff_sold_seats == 0:
                return_value += f"{category.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)}" \
                                f"{f''.ljust(7)} {percentage_sold:.1f}%\n"
            else:
                return_value += f"{category.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)}" \
                                f"{f'{diff_sold_seats:+}'.ljust(7)} {percentage_sold:.1f}%\n"

        else:
            return_value += (f"{category.ljust(10)} {f'{sold_seats}/{total_capacity}'.ljust(12)} "
                             f"{percentage_sold:.1f}%\n")
    time_now = get_time_formatted("human")
    return_value += f"\n\nOppdatert: {time_now}\n "
    return return_value


def create_seasonpass_string(dir_path: str) -> str:
    """Creates a formatted string with season pass information for a tweet.

    The function generates a string with season pass information, including differences in pass sales
    compared to the previous data point, ready to be posted as a tweet.
    Args:
        dir_path (str):
            The path to the event directory.
    Returns:
        str:
            A string containing the formatted season pass information.
    """
    if "eliteserien" in dir_path.lower():
        return_value = "Partoutkort Eliteserien"
    elif "toppserien" in dir_path.lower():
        return_value = "Partoutkort Toppserien"
    else:
        return "Error"

    sold_seats = 0
    latest, prior = get_latest_file(dir_path)
    for category, data in latest.items():
        if category.lower() == "totalt":
            return_value += "\n"

            sold_seats = data["sold_seats"]

            diff_sold_seats = 0
            if prior is not None:
                prior_sold_seats = prior[category]["sold_seats"]

                diff_sold_seats = sold_seats - prior_sold_seats

            return_value += (f"\nDet er solgt: {sold_seats}\n"
                             f"{diff_sold_seats:+} siden sist")
    disclaimer = True
    remaining = max(0, 10100 - sold_seats)
    if "eliteserien" in dir_path.lower() and disclaimer:
        return_value += (f"\n"
                         f"\nOmkring {remaining} billetter igjen!\n\n"
                         f"\n(Siste offisielle tall er 9600"
                         f"\nsolgte. Postet 27/02/24 19:12)\n")
    elif "eliteserien" in dir_path.lower():
        return_value += "\n\n\n\n\n\n\n"
    elif "toppserien" in dir_path.lower():
        return_value += "\n\n\n\n\n\n\n"

    time_now = get_time_formatted("human")
    return_value += f"\nOppdatert: {time_now}\n "

    return return_value


def create_soldout_string(dir_path: str) -> str:
    """Creates a formatted string with sold out information for a tweet.

    The function generates a string that says sold out and is ready to be posted as a tweet.
    Args:
        dir_path (str):
            The path to the event directory.
    Returns:
        str:
            A string containing the formatted season pass information.
    """
    latest, prior = get_latest_file(dir_path)
    return_value = ""

    for category, data in latest.items():
        if "GENERAL" in category:
            return_value = data["title"] + "\n" + data["date"] + "\n\n"
            return_value += "\n\n\n          UTSOLGT!!\n\n\n\n\n"

            time_now = get_time_formatted("human")
            return_value += f"\nOppdatert: {time_now}\n "

            return return_value

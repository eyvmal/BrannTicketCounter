from typing import Tuple, List

import PIL.Image
import os
import textwrap

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

# Copy of code found here: https://rk.edu.pl/en/generating-memes-and-infographics-with-pillow/
# Used to add text under a logo image

SAVE_PATH = os.path.dirname(os.path.abspath(__file__)) + "/"
FONT_PATH = "imagify/SFMonoRegular.otf"  # Path from this file
SERIEN = "Eliteserien 2023"


class Imagify:
    BACKGROUND_COLOR = (227, 26, 34)  # Red color as RGB tuple
    TEXT_COLOR = (255, 255, 255)  # White color as RGB tuple

    def __init__(self, image_path, caption):
        self.image_path = image_path
        self.caption = caption

    def generate(self):
        print("Generating image... ", end="")
        image = self._get_image_object()
        text_image = get_text_as_image(
            self.caption, text_color=self.TEXT_COLOR, text_size=95, image_width=image.size[0],
            background_color=self.BACKGROUND_COLOR)
        image = bottom_expand_image_with_image(image, text_image, background_color=self.BACKGROUND_COLOR)
        image = draw_border(image, border_size=10, border_color=self.BACKGROUND_COLOR)
        print("DONE")
        return image

    def _get_image_object(self):
        return PIL.Image.open(self.image_path)


def draw_border(image, border_size, border_color):
    original_width, original_height = image.size
    width = original_width + border_size * 2
    height = original_height + border_size * 2
    border_canvas = PIL.Image.new('RGB', (width, height), border_color)
    border_canvas.paste(image, (border_size, border_size))
    return border_canvas


def get_text_as_image(text, text_color, text_size, image_width, background_color):
    placeholder = PIL.Image.new('RGB', (0, 0), background_color)
    font = get_font(size=text_size)
    draw_canvas = PIL.ImageDraw.Draw(placeholder)
    text_width, text_height = draw_canvas.textsize(text, font=font)
    if text_width > image_width:
        print("Text too big")
        character_width = text_width / len(text)
        max_characters_count = int(image_width / character_width)
        text_lines = wrap_text(text, wrap_width=max_characters_count)
    else:
        text_lines = [text]

    total_text_height = len(text_lines) * text_height
    image = PIL.Image.new('RGB', (image_width, total_text_height), background_color)
    draw_canvas = PIL.ImageDraw.Draw(image)

    for row, line in enumerate(text_lines):
        row_height = row * text_height
        line_width, _ = draw_canvas.textsize(line, font=font)
        left = (image_width - line_width) / 2
        draw_canvas.text((left, row_height), line, fill=text_color, font=font)
    return image


def bottom_expand_image_with_image(image, expand_image, background_color):
    width = image.size[0]
    height = image.size[1] + expand_image.size[1]
    expand_canvas = PIL.Image.new('RGB', (width, height), background_color)
    expand_canvas.paste(image, (0, 0))
    expand_canvas.paste(expand_image, (0, image.size[1]))
    return expand_canvas


def wrap_text(text, wrap_width):
    wrapper = textwrap.TextWrapper(width=wrap_width)
    return wrapper.wrap(text)


def get_font(size):
    path = os.path.join(SAVE_PATH + FONT_PATH)
    return PIL.ImageFont.truetype(path, size=size)


# ("keyword"): ("image_name", "title"),
IMAGE_MAP = {
    ("aalesund", "ålesund"): ("aalesund.png", "Brann - Aalesund"),
    ("bodø",): ("bodoglimt.png", "Brann - Bodø/Glimt"),
    ("godset",): ("godset.png", "Brann - Strømsgodset"),
    ("hamkam", "hamar"): ("hamkam.png", "Brann - HamKam"),
    ("haugesund",): ("haugesund.png", "Brann - Haugesund"),
    ("lillestrøm",): ("lillestrom.png", "Brann - Lillestrøm"),
    ("molde",): ("molde.png", "Brann - Molde"),
    ("odd",): ("odd.png", "Brann - Odd"),
    ("rosenborg",): ("rosenborg.png", "Brann - Rosenborg"),
    ("sandefjord",): ("sandefjord.png", "Brann - Sandefjord"),
    ("sarpsborg",): ("sarpsborg.png", "Brann - Sarpsborg"),
    ("stabæk",): ("stabek.png", "Brann - Stabæk"),
    ("tromsø",): ("tromso.png", "Brann - Tromsø"),
    ("vålerenga",): ("valrengen.png", "Brann - Vålerenga"),
    ("viking",): ("viking.png", "Brann - Viking"),
    ("alkmaar",): ("alkmaar.png", "Brann - AZ Alkmaar"),
    ("glasgow",): ("brann_logo.png", "UEFA CL Runde 2: Brann - Glasgow City"),
    ("praha",): ("brann_logo.png", "UEFA CL Group B: Brann - Slavia Praha"),
}


def get_image(line: str) -> Tuple[str, str]:
    """
    Retrieves the associated image path and title based on keywords found in the provided line.
    This function searches for keywords within the provided line. Based on these keywords,
    it returns the corresponding image path and title. If no keyword is matched, a default
    image and title (the line itself) is returned.
    Args:
        line (str): The line of text containing the match title from ticketco.
    Returns:
        Tuple[str, str]:
            - The full path to the associated or default image.
            - The title or header associated with the matched keyword or the truncated line itself.
    """
    line_lower = line.lower()

    for keywords, (image_name, title) in IMAGE_MAP.items():
        if any(keyword in line_lower for keyword in keywords):
            return f"{SAVE_PATH}imagify/{image_name}", title

    # default case
    if len(line) > 40:  # Cuts the line at the 40th character to prevent formatting error
        line = line[:40]
    return SAVE_PATH + "imagify/brann_logo.png", line


def generate_images(strings: List[str]) -> List[str]:
    """
    Generates images based on the provided list of match titles.
    For each string in the provided list, this function determines the appropriate image
    and modifies the string's header.
    Args:
        strings (List[str]): A list of strings containing the match titles from ticketco.
    Returns:
        List[str]:
            A list containing the paths to the generated images.
    """
    iteration = 0
    image_paths = []
    for string in strings:
        # Split the string in lines and use the first line to fetch image_path and a custom header
        lines = string.splitlines()
        image_path, lines[0] = get_image(str(lines[0]))
        modified_string = '\n'.join(lines)

        # Image output name
        image_name = "ticket_sale_result" + str(iteration) + ".jpg"

        # Create the images using the image path and the modified_string
        image_object = Imagify(os.path.join(image_path), modified_string).generate()
        image_object.save(image_name, quality=90)
        iteration += 1
        image_paths.append(image_name)
    return image_paths

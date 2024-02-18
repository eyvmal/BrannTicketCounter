from typing import Tuple, List

from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

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
        print("DONE")
        return image

    def _get_image_object(self):
        return Image.open(self.image_path)


def draw_border(image, border_size, border_color):
    original_width, original_height = image.size
    width = original_width + border_size * 2
    height = original_height + border_size * 2
    border_canvas = Image.new('RGB', (width, height), border_color)
    border_canvas.paste(image, (border_size, border_size))
    return border_canvas


def get_text_as_image(text, text_color, text_size, image_width, background_color):
    placeholder = Image.new('RGB', (0, 0), background_color)
    font = get_font(size=text_size)
    draw_canvas = ImageDraw.Draw(placeholder)
    text_width, text_height = draw_canvas.textsize(text, font=font)
    if text_width > image_width:
        print("Text too big")
        character_width = text_width / len(text)
        max_characters_count = int(image_width / character_width)
        text_lines = wrap_text(text, wrap_width=max_characters_count)
    else:
        text_lines = [text]

    total_text_height = len(text_lines) * text_height
    image = Image.new('RGB', (image_width, total_text_height), background_color)
    draw_canvas = ImageDraw.Draw(image)

    for row, line in enumerate(text_lines):
        row_height = row * text_height
        line_width, _ = draw_canvas.textsize(line, font=font)
        left = (image_width - line_width) / 2
        draw_canvas.text((left, row_height), line, fill=text_color, font=font)
    return image


def bottom_expand_image_with_image(image, expand_image, background_color):
    width = image.size[0]
    height = image.size[1] + expand_image.size[1]
    expand_canvas = Image.new('RGB', (width, height), background_color)
    expand_canvas.paste(image, (0, 0))
    expand_canvas.paste(expand_image, (0, image.size[1]))
    return expand_canvas


def wrap_text(text, wrap_width):
    wrapper = textwrap.TextWrapper(width=wrap_width)
    return wrapper.wrap(text)


def get_font(size):
    path = os.path.join(SAVE_PATH + FONT_PATH)
    return ImageFont.truetype(path, size=size)


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
        full_image_path = os.path.join(SAVE_PATH, image_name)
        image_object.save(full_image_path, quality=90)
        iteration += 1
        image_paths.append(full_image_path)
    return image_paths


# ("keyword"): ("image_name", "title"),
IMAGE_MAP = {
    ("aalesund", "ålesund"): ("alesund.png", "Brann - Aalesund"),
    ("bodø",): ("bodoglimt.png", "Brann - Bodø/Glimt"),
    ("fredrikstad",): ("fredrikstad.png", "Brann - Fredrikstad"),
    ("hamkam", "hamar"): ("hamkam.png", "Brann - HamKam"),
    ("haugesund",): ("haugesund.png", "Brann - Haugesund"),
    ("kfum",): ("kfum.png", "Brann - KFUM Oslo"),
    ("kristiansund",): ("kristiansund.png", "Brann - Kristiansund"),
    ("lillestrøm",): ("lillestrom.png", "Brann - Lillestrøm"),
    ("molde",): ("molde.png", "Brann - Molde"),
    ("odd",): ("odd.png", "Brann - Odd"),
    ("rosenborg",): ("rosenborg.png", "Brann - Rosenborg"),
    ("sandefjord",): ("sandefjord.png", "Brann - Sandefjord"),
    ("sarpsborg",): ("sarpsborg.png", "Brann - Sarpsborg"),
    ("stabæk",): ("stabek.png", "Brann - Stabæk"),
    ("strømsgodset",): ("stromsgodset.png", "Brann - Strømsgodset"),
    ("tromsø",): ("tromso.png", "Brann - Tromsø"),
    ("vålerenga",): ("valrenga.png", "Brann - Vålerenga"),
    ("viking",): ("viking.png", "Brann - Viking"),
    ("alkmaar",): ("alkmaar.png", "Brann - AZ Alkmaar"),
    ("glasgow",): ("default.png", "UEFA CL Runde 2: Brann - Glasgow City"),
    ("praha",): ("default.png", "UEFA CL Group B: Brann - Slavia Praha"),
    ("lyon",): ("lyon.png", "UEFA CL Group B: Brann - Lyon"),
    ("pölten",): ("polten.png", "UEFA CL Group B: Brann - St. Pölten"),
    ("barcelona",): ("barcelona_femini.png", "UEFA CL Kvartfinale: Brann - Barcelona"),
    ("partoutkort eliteserien",): ("eliteserien_logo.png", "\nPartoutkort Eliteserien 2024"),
    ("partoutkort toppserien",): ("toppserien_logo.png", "\nPartoutkort Toppserien 2024"),
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
            if "partoutkort" in line_lower:
                return f"{SAVE_PATH}imagify/{image_name}", title
            path1, path2 = f"{SAVE_PATH}imagify/brann.png", f"{SAVE_PATH}imagify/{image_name}"
            return stitch_images(path1, path2), title

    # default case
    if len(line) > 35:  # Cuts the line at the 40th character to prevent formatting error
        line = line[:35]
    return f"{SAVE_PATH}imagify/default.png", line


def stitch_images(image_path1, image_path2):
    """
    Method to stitch together two logos and return the path to a
    temp_image where they're stitched together.
    """
    def paste_centered(image, canvas_size, background_color):
        canvas = Image.new("RGB", canvas_size, background_color)
        alpha = image.split()[3] if len(image.split()) == 4 else None
        x_offset = (canvas_size[0] - image.width) // 2
        y_offset = (canvas_size[1] - image.height) // 2
        canvas.paste(image, (x_offset, y_offset), mask=alpha)
        return canvas

    def combine_horizontally(img1, img2, background_color):
        new_width = img1.width + img2.width
        new_height = max(img1.height, img2.height)

        combined_image = Image.new("RGB", (new_width, new_height), background_color)
        combined_image.paste(img1, (0, 0), mask=img1.split()[3] if len(img1.split()) == 4 else None)
        combined_image.paste(img2, (img1.width, 0), mask=img2.split()[3] if len(img2.split()) == 4 else None)

        return combined_image

    image1 = Image.open(image_path1)
    image2 = Image.open(image_path2)

    logo_size = (1200, 1200)
    background_color_rgb = (227, 26, 34)

    # Paste each image onto a blank canvas
    canvas1 = paste_centered(image1, logo_size, background_color_rgb)
    canvas2 = paste_centered(image2, logo_size, background_color_rgb)

    # Combine the canvases horizontally
    result_image = combine_horizontally(canvas1, canvas2, background_color_rgb)

    # Save or display the result
    result_image.save(f"{SAVE_PATH}imagify/temp.png")  # Save the result to a file
    return f"{SAVE_PATH}imagify/temp.png"

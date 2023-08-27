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


def get_image(line):
    if "aalesund" in line or "ålesund" in line:
        return SAVE_PATH + "imagify/aalesund.png"
    elif "bodø" in line:
        return SAVE_PATH + "imagify/bodoglimt.png"
    elif "godset" in line:
        return SAVE_PATH + "imagify/godset.png"
    elif "hamar" in line:
        return SAVE_PATH + "imagify/hamkam.png"
    elif "haugesund" in line:
        return SAVE_PATH + "imagify/haugesund.png"
    elif "lillestrøm" in line:
        return SAVE_PATH + "imagify/lillestrøm.png"
    elif "molde" in line:
        return SAVE_PATH + "imagify/molde.png"
    elif "odd" in line:
        return SAVE_PATH + "imagify/odd.png"
    elif "rosenborg" in line:
        return SAVE_PATH + "imagify/rosenborg.png"
    elif "sandefjord" in line:
        return SAVE_PATH + "imagify/sandefjord.png"
    elif "sarpsborg" in line:
        return SAVE_PATH + "imagify/sarpsborg.png"
    elif "stabæk" in line:
        return SAVE_PATH + "imagify/stabek.png"
    elif "tromsø" in line:
        return SAVE_PATH + "imagify/tromso.png"
    elif "vålrenga" in line:
        return SAVE_PATH + "imagify/valrengen.png"
    elif "viking" in line:
        return SAVE_PATH + "imagify/viking.png"
    elif "alkmaar" in line:
        return SAVE_PATH + "imagify/alkmaar.png"
    else:
        return SAVE_PATH + "imagify/brann_logo.jpeg"

import requests
from bs4 import BeautifulSoup
import tinycss2
import re
import random
from collections import Counter
from PIL import Image
from io import BytesIO
from sklearn.cluster import KMeans
import numpy as np
import cv2

def fetch_url(url):
    if url.startswith('//'):
        url = 'https:' + url
    response = requests.get(url)
    response.raise_for_status()
    return response

def get_brand_logos(url):
    soup = BeautifulSoup(fetch_url(url).text, 'html.parser')
    images = soup.find_all('img')
    logos = []
    for image in images:
        if 'logo' in image.get('src', ''):
            logo_url = image['src']
            if logo_url.startswith('//'):
                logo_url = 'https:' + logo_url
            # print(logo_url)
            primary_color = get_primary_color(logo_url)
            logos.append((logo_url, primary_color))
    return logos

def get_primary_color(image_url):
    # Fetch the image from the URL
    response = fetch_url(image_url)
    img = Image.open(BytesIO(response.content))

    # Check if the image has an alpha (transparency) channel
    if img.mode == 'RGBA':
        # Convert the image into an array
        ar = np.asarray(img)

        # Remove transparent pixels (alpha < 128)
        ar = ar[ar[..., 3] >= 128]

        # If all pixels are transparent, return None
        if len(ar) == 0:
            return None

        # Reshape the array to be two-dimensional
        ar = ar[:, :3].reshape((-1, 3))
    else:
        # If the image doesn't have an alpha channel, convert it to RGB and proceed as before
        img = img.convert('RGB')
        img = img.resize((50, 50))
        ar = np.asarray(img)
        ar = ar.reshape((-1, 3))

    # Run KMeans to find the most dominant color
    kmeans = KMeans(n_clusters=1)
    kmeans.fit(ar)

    # Convert the dominant color to hexadecimal
    color = '#%02x%02x%02x' % tuple(map(int, (kmeans.cluster_centers_[0])))
    return color

def get_color_frequency(url):
    soup = BeautifulSoup(fetch_url(url).text, 'html.parser')
    stylesheets = [link["href"] for link in soup.findAll('link', {'rel': 'stylesheet'}) if "href" in link.attrs]

    color_values = []
    hex_colors = re.compile(r'#[0-9a-fA-F]{6}')
    for i, stylesheet in enumerate(stylesheets):
        response = fetch_url(stylesheet)
        color_values.extend(parse_css(response.text, hex_colors))

    return dict(Counter(color_values))

def parse_css(css, hex_colors):
    parsed_css = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    color_values = []
    for rule in parsed_css:
        if rule.type == 'qualified-rule':
            content = tinycss2.serialize(rule.content)
            if 'color' in content.lower():
                color_values.extend(hex_colors.findall(content))
    return color_values

def get_images(url):
    soup = BeautifulSoup(fetch_url(url).text, 'html.parser')
    images = soup.find_all('img')
    image_urls = []
    for image in images:
        img_url = image.get('src', '')
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        image_urls.append(img_url)
    image_urls = [u for u in image_urls if (u and 'logo' not in u)]
    # print(image_urls)
    ret_dict = {
        'products': [],
        'general': []
    }
    for u in image_urls:
        if '/products/' in u:
            category = 'products'
        else:
            category = 'general'
        ret_dict[category].append(u)
    return ret_dict

def get_fonts(url):
    soup = BeautifulSoup(fetch_url(url).text, 'html.parser')
    stylesheets = [link["href"] for link in soup.findAll('link', {'rel': 'stylesheet'}) if "href" in link.attrs]

    font_declarations = []
    for stylesheet in stylesheets:
        response = fetch_url(stylesheet)
        font_declarations.extend(extract_font_declarations(response.text))

    fonts = {
        'header': [],
        'body': []
    }

    for font_declaration in font_declarations:
        font_family = extract_font_family(font_declaration)
        if 'h1' in font_declaration or 'h2' in font_declaration or 'h3' in font_declaration or \
           'h4' in font_declaration or 'h5' in font_declaration or 'h6' in font_declaration:
            fonts['header'].append(font_family)
        else:
            fonts['body'].append(font_family)

    # Removing duplicates and returning
    fonts['header'] = [e for e in set(fonts['header']) if 'inheri' not in e]
    fonts['body'] = [e for e in set(fonts['body']) if 'inheri' not in e]

    return fonts

def extract_font_declarations(css):
    parsed_css = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    font_declarations = []
    for rule in parsed_css:
        if rule.type == 'qualified-rule':
            content = tinycss2.serialize(rule.content)
            if 'font-family' in content.lower():
                font_declarations.append(content)
    return font_declarations

def extract_font_family(css_declaration):
    start = css_declaration.find('font-family:') + len('font-family:')
    end = css_declaration.find(';', start)
    font_family = css_declaration[start:end].strip()
    return font_family

def contrast_ratio(color1, color2):
    """Compute contrast ratio according to WCAG formula."""
    def to_linear(c):
        c = c / 255.0
        if c <= 0.03928:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    def luminance(color):
        r, g, b = (to_linear(int(color[i:i+2], 16)) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1, l2 = sorted((luminance(color1), luminance(color2)))

    return (l1 + 0.05) / (l2 + 0.05) if l1 > l2 else (l2 + 0.05) / (l1 + 0.05)

def find_most_contrastive_color(color, color_list):
    """Find the most contrastive color from a list."""
    
    def hex_to_rgb(hex):
        return tuple(int(hex[i:i+2], 16) / 255 for i in (1, 3, 5))

    def luminance(color):
        r, g, b = color
        gamma = lambda x : ((x + 0.055) / 1.055) ** 2.4 if x > 0.03928 else x / 12.92
        return 0.2126 * gamma(r) + 0.7152 * gamma(g) + 0.0722 * gamma(b)

    def contrast_ratio(color1, color2):
        l1, l2 = sorted((luminance(color1), luminance(color2)), reverse=True)
        return (l1 + 0.05) / (l2 + 0.05)

    # Convert hex colors to RGB
    rgb_color = hex_to_rgb(color)
    rgb_color_list = [hex_to_rgb(c) for c in color_list]

    # Compute the contrast ratio between the given color and each color in the list
    contrast_ratios = [(contrast_ratio(rgb_color, c), hex_color) for c, hex_color in zip(rgb_color_list, color_list)]

    # Return the color with the highest contrast ratio
    _, most_contrastive_color = max(contrast_ratios)
    
    return most_contrastive_color


def assign_colors(colors):
    n = len(colors)
    assignment = {}
    
    # For background and body colors, choose two random, but different, colors
    random_colors = random.sample(colors, 2)
    assignment['background color'] = random_colors[0]
    assignment['section background color'] = random_colors[1]

    # For text colors, choose the color that contrasts most with the body color
    body_color = assignment['section background color']
    contrast_with_body = sorted(colors, key=lambda color: contrast_ratio(color, body_color))
    assignment['header text color'] = contrast_with_body[-1]
    assignment['body text color'] = contrast_with_body[-2 if n > 1 else -1]

    # For the primary color, choose a color that contrasts with the background
    background_color = assignment['background color']
    contrast_with_background = sorted(colors, key=lambda color: contrast_ratio(color, background_color))
    assignment['primary color'] = contrast_with_background[-1]

    # For the accent color, choose a color that contrasts with the primary color
    primary_color = assignment['primary color']
    contrast_with_primary = sorted(colors, key=lambda color: contrast_ratio(color, primary_color))
    assignment['accent color'] = contrast_with_primary[-1 if n > 1 else -1]

    # For button colors, choose a color that contrasts with the body color
    assignment['button color'] = contrast_with_body[-1 if n > 1 else -1]

    # For button text colors, choose a color that contrasts with the button color
    button_color = assignment['button color']
    contrast_with_button = sorted(colors, key=lambda color: contrast_ratio(color, button_color))
    assignment['button text color'] = contrast_with_button[-1]

    return assignment

def get_header_texts(url):
    soup = BeautifulSoup(fetch_url(url).text, 'html.parser')
    headers = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    header_texts = []

    for header in headers:
        for tag in soup.find_all(header):
            header_texts.append(tag.get_text())

    return list(set(h for h in header_texts if h))
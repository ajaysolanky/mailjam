import re
import json
import time
import requests
import random
from bs4 import BeautifulSoup, Comment

from brand_kit import get_brand_logos, get_color_frequency, get_images, get_fonts, assign_colors, get_header_texts, find_most_contrastive_color
from utils import openai_query, get_unsplash_url, get_product_description, get_google_font_link, flatten_list

class EmailGenerator(object):
    def __init__(self) -> None:
        self.query_openai_fn = openai_query
        ###
        self.product_photos = []
        self.page_photos = []
        self.headers = []

    def generate(self, query, url):
        # url = 'https://www.marble-lotus.com'
        print('getting brand kit')
        brand_assets = self.get_brand_assets(url)
        brand_theme_kit = {k:brand_assets[k] for k in brand_assets if k in ['logoURL', 'colors', 'fonts']}
        brand_photo_assets = brand_assets['photos']
        self.product_photos = brand_photo_assets['products']
        self.page_photos = brand_photo_assets['general']
        self.headers = brand_assets['headers']
        font_list = flatten_list([v for k,v in brand_theme_kit['fonts'].items()])
        # print(brand_assets)
        print('parsing query')
        email_info = self.parse_query(query)
        print(email_info)
        print('generating email structure')
        code_skeleton = self.get_code_skeleton(email_info)
        print('extracting mj sections and getting theme template')
        section_xml_li = self.extract_mj_sections(code_skeleton)
        theme_template = self.get_theme_template()
        print('filling individual sections')
        for section_xml in section_xml_li:
            section_name = self.extract_single_comment(section_xml)
            section_info = {
                'name': section_name
            }
            print(f'filling {section_name} section')
            self.fill_section(email_info, section_info, section_xml, theme_template)
        all_xml_str = str(code_skeleton)
        print('generating theme')
        theme_map = self.generate_theme_map(email_info, theme_template, brand_theme_kit)
        # print(theme_map)
        print('applying theme')
        themed_xml_str = self.apply_theme_map(all_xml_str, theme_map)
        with_unsplash_photos_xml = self.replace_aesthetic_photo_descriptions(themed_xml_str)
        with_product_photos_xml = self.replace_product_photo_descriptions(with_unsplash_photos_xml)
        with_product_blurb_xml = self.replace_product_blurb_descriptions(with_product_photos_xml)
        fixed_stuff = self.fix_stuff(with_product_blurb_xml)
        print("building head")
        head_str = self.build_mjml_head(font_list)
        fixed_stuff = fixed_stuff.replace('<?xml version="1.0" encoding="utf-8"?>', '').strip()
        open_tag = '<mjml>'
        fixed_stuff = fixed_stuff[:len(open_tag)] + head_str + fixed_stuff[len(open_tag):]
        with_company_name = self.replace_company_name(url, fixed_stuff)

        print(f'final mjml:\n\n{with_company_name}')
        return with_company_name

    def parse_query(self, query):
        prompt_template = """A user is building an e-commerce marketing email using generative AI, and this is part of the workflow.
He is inputting a single natural language query, and your task is to return a json object with the relevant fields parsed.

The fields you should extract are:

type: What kind of business are we building this email for? (e.g. sporting goods, photography services, men's underwear, etc)
layout_info: Provide any information relevant to how the user wants the email laid out (e.g. single hero product at the top)
theme_info: Provide any information relevant to how the user wants the email theme to look (e.g. summery colors, blue accents, etc)
other_info: Any other information that is likely to be relevant when building the email

USER QUERY:
An email for a sporting goods store, should have a product gallery midway down the email and a color palette that's evocative of f1 racing. Include some written and visual content about f1 racing.

OUTPUT:
{{
    "type": "sporting goods",
    "layout_info": "product gallery midway down",
    "theme_info": "color palette that's evocative of f1 racing",
    "other_info": "include written and visual content about f1 racing"
}}

------------------

USER QUERY:
{user_query}
"""
        prompt = prompt_template.format(user_query = query)
        openai_resp = self.query_openai_fn(prompt)
        json_idx = 0
        try:
            json_idx = openai_resp.index('OUTPUT:') + len('OUTPUT:')
        except:
            pass
        return json.loads(openai_resp[json_idx:])

    def get_code_skeleton(self, email_info):
        prompt_template = """Give me the high level MJML framework for a marketing email for pet supplies. Just give the first-level mj-sections and pseudocode, don't fill anything in under those first-level "mj-section" tags.

MJML:```<mjml>
<mj-body background-color="$background_color$">
    <!-- Header Section -->
    <mj-section>
    <!-- Header Contents Here -->
    </mj-section>

    <!-- Hero Image Section -->
    <mj-section>
    <!-- Hero Image Contents Here -->
    </mj-section>

    <!-- Product Highlight Section -->
    <mj-section>
    <!-- Product Highlight Contents Here -->
    </mj-section>

    <!-- Additional Products Section -->
    <mj-section>
    <!-- Additional Products Contents Here -->
    </mj-section>

    <!-- Testimonial Section -->
    <mj-section>
    <!-- Testimonial Contents Here -->
    </mj-section>

    <!-- Call to Action Section -->
    <mj-section>
    <!-- Call to Action Contents Here -->
    </mj-section>

    <!-- Footer Section -->
    <mj-section>
    <!-- Footer Contents Here -->
    </mj-section>
</mj-body>
</mjml>```

------------------

Give me the high level MJML framework for a marketing email for {email_type}. Just give the first-level mj-sections and pseudocode, don't fill anything in under those first-level "mj-section" tags.

MJML:```
"""
        prompt = prompt_template.format(email_type=email_info['type'])
        # openai_resp = self.query_openai_fn(prompt)
        openai_resp = """<mjml>
<mj-body background-color="$background_color$">
    <!-- Header Section -->
    <mj-section>
    <!-- Header Contents Here -->
    </mj-section>

    <!-- Hero Image Section -->
    <mj-section>
    <!-- Hero Image Contents Here -->
    </mj-section>

    <!-- Two Column Product Gallery Section -->
    <mj-section>
    <!-- Two Column Product Gallery Contents Here -->
    </mj-section>

    <!-- Footer Section -->
    <mj-section>
    <!-- Footer Contents Here -->
    </mj-section>
</mj-body>
</mjml>```"""
        return BeautifulSoup(openai_resp[:openai_resp.index('```')], 'xml')
    
    def extract_mj_sections(self, soup):
        mj_sections = soup.find_all('mj-section')
        return mj_sections

    def extract_single_comment(self, mj_section):
        comment = mj_section.find(string=lambda text: isinstance(text, Comment))
        return comment

    def modify_mj_section(self, mj_section, new_content):
        # Create a new BeautifulSoup object from the new_content string
        new_content_soup = BeautifulSoup(new_content, 'xml')

        # Filter out comments and check if the parsed XML has exactly one root tag and that tag is 'mj-section'
        root_tags = [tag for tag in new_content_soup.contents if not isinstance(tag, Comment)]
        if len(root_tags) != 1 or root_tags[0].name != 'mj-section':
            raise ValueError("new_content must be a well-formed XML string that contains a single 'mj-section' tag")

        # Get the first child of the root tag to get the actual 'mj-section' tag.
        new_mj_section = root_tags[0]

        # Replace the old 'mj-section' tag with the new one.
        mj_section.replace_with(new_mj_section)

    def get_brand_assets(self, url):
        logos = get_brand_logos(url)
        color_freq_dict = get_color_frequency(url)
        color_list = [v[0] for v in sorted(color_freq_dict.items(), key=lambda x: x[1], reverse=True)]
        photos = get_images(url)
        headers = get_header_texts(url) 
        fonts = get_fonts(url)
        for key in fonts:
            new_li = []
            for el in fonts[key]:
                font_name = el[:el.index(',')] if ',' in el else el
                font_link = get_google_font_link(font_name)
                if font_link:
                    new_li.append(font_name)
            fonts[key] = new_li
        
        colors = assign_colors(color_list[:5])
        bg_color = colors['section background color']
        ccolor = find_most_contrastive_color(bg_color, [c for l,c in logos])
        logoUrl = None
        for l, c in logos:
            if c == ccolor:
                logoUrl = l

        return {
            'logoURL': logoUrl,
            'colors': colors,
            'photos': photos,
            'fonts': fonts,
            'headers': headers
        }
        # return {
        #     'logoURL': logo_url,
        #     'colors': {
        #         'primary': color_list[0],
        #         'secondary': color_list[1],
        #         'tertiary': color_list[2],
        #         'quaternary': color_list[3],
        #         'quinary': color_list[4],
        #         'senary': color_list[5],
        #         'septenary': color_list[6],
        #         'octonary': color_list[7],
        #         'nonary': color_list[8],
        #         'denary': color_list[9]
        #     },
        #     'photos': photos,
        #     'fonts': fonts
        # }

    def get_theme_template(self):
        theme_template = {
            "theme": {
                "backgroundColor": "$background_color$",
                "sectionBackgroundColor": "$section_background_color$",
                "primaryColor": "$primary_color$",
                "accentColor": "$accent_color$",
                "headerTextColor": "$header_text_color$",
                "bodyTextColor": "$body_text_color$",
                "footerTextColor": "$footer_text_color$",
                "buttonTextColor": "$button_text_color$",
                "buttonBackgroundColor": "$button_background_color$",
                "headerFont": "$header_font$",
                "bodyFont": "$body_font$",
            },
            "company": {
                "name": "$company_name$",
                "address": "123 Main St, Anytown, USA",
                "logoUrl": "$logo_url$",
            },
            "email": {
                "ctaUrl": "https://www.google.com",
            },
        }

        return theme_template
    
    def generate_theme_map(self, email_info, theme_template, brand_kit):
        theme_template_json = json.dumps(theme_template)
        brand_kit_json = json.dumps(brand_kit)

        prompt_template = """I am creating an email template for a marketing email for a {business_type} company.
I would like to set a theme for the email that is consistent with what I would expect from an email from a {business_type} company.

Here is a json string representing all the values that need to be set for the theme:

INPUT JSON:
{theme_template_json}

Can you take that json string and return a json string with all the fields that haven't yet been filled out? Fields that haven't been filled out will look like "<field>". Don't overwrite any fields that have already been filled out.

Use interesting fonts and colors that are relevant ot what the email is trying to accomplish.

Some additional info you may want to consider are:
Additional Layout Info: {layout_info}
Additional Theme Info: {theme_info}
Other Info: {other_info}

Also consider consider the following brand kit that the company has provided. The colors provided in the brand kit are in no particular order:
{brand_kit_json}

Try to stay close to the kit, but feel free to alter colors if it makes sense.

OUTPUT JSON:

"""

        prompt = prompt_template.format(
            business_type=email_info['type'],
            layout_info=email_info['layout_info'],
            theme_info=email_info['theme_info'],
            other_info=email_info['other_info'],
            theme_template_json=theme_template_json,
            brand_kit_json=brand_kit_json,
        )

        nested_theme_dict = json.loads(self.query_openai_fn(prompt))
        flat_theme_dict = self.flatten_dict(nested_theme_dict)
        flat_theme_template = self.flatten_dict(theme_template)
        theme_map = {flat_theme_template[k]:flat_theme_dict[k] for k in flat_theme_template}
        return theme_map
    
    def flatten_dict(self, d):
        items = {}
        for k, v in d.items():
            if isinstance(v, dict):
                items.update(self.flatten_dict(v))
            else:
                items[k] = v
        return items
    
    def apply_theme_map(self, xml_str, theme_map):
        for key, val in theme_map.items():
            xml_str = xml_str.replace(key, val)
        return xml_str
    
    def fill_section(self, email_info, section_info, section_xml, theme_template):
        email_type = email_info['type']
        def extract_section_name(s):
            match = re.search('(.*?) Contents Here', s)
            if match:
                return match.group(1)
            else:
                return None
        section_name =  extract_section_name(section_info['name']).strip()

        prompt_template = """Generate the MJML markdown code for the {section_type} section for a marketing email for {email_type}.
Only generate the markdown code for a single {section_type} section and nothing further, I will generate the other sections at a later step.

Think carefully about what kind of structure is best for a {section_type} section.

Some additional info you may want to consider are:
Additional Layout Info: {layout_info}
Additional Theme Info: {theme_info}
Other Info: {other_info}

Feel free to use product images and other aesthetic photos that would complement the email well.

If you want to use a product image, please just insert $product_photo:<product text description>$ as a placeholder. If you want to include a written product description, just write $product_blurb:<product text description>$ as a placeholder.
If you want to use a general image that would be aesthetic within the email, just insert $aesthetic_photo:<photo text description>$ as a placeholder.

Use the theme described in this JSON file. Fully apply this theme to this section to make the document stylistically consistent. The json file contains several placeholder variables, just place those in directly and I will swap them out later manually:
{theme_template}

In order to convey an authentic brand voice, try to borrow from some of the headers on the website when writing copy for the email:
{headers}

MJML:```{starter}
"""
        starter = f"<!-- {section_name} Section -->\n<mj-section "
        section_type = section_name
        prompt = prompt_template.format(
            email_type=email_type,
            layout_info=email_info['layout_info'],
            theme_info=email_info['theme_info'],
            other_info=email_info['other_info'],
            theme_template=theme_template,
            starter=starter,
            section_type=section_type,
            headers=self.headers)
        openai_resp = self.query_openai_fn(prompt)
        new_content = starter + openai_resp[:openai_resp.index('```')]
        self.modify_mj_section(section_xml, new_content)

    def replace_placeholder_general(self, xml_str, tag, query_fn):
        # Regular expression pattern to find '${tag}:<product description>$'
        pattern = fr"\${tag}:(.*?)\$"
        # pattern = r"\$aesthetic_photo:(.*?)\$"
        
        def replacement_func(match):
            product_description = match.group(1)  # Extract product description
            # print(product_description)
            replacement_string = query_fn(product_description)
            return replacement_string

        result_string = re.sub(pattern, replacement_func, xml_str)
        return result_string

    def replace_aesthetic_photo_descriptions(self, xml_str):
        # return self.replace_placeholder_general(xml_str, 'aesthetic_photo', get_unsplash_url)
        return self.replace_placeholder_general(xml_str, 'aesthetic_photo', self.get_page_photo)

    def replace_product_photo_descriptions(self, xml_str):
        return self.replace_placeholder_general(xml_str, 'product_photo', self.get_product_photo)

    def replace_product_blurb_descriptions(self, xml_str):
        return self.replace_placeholder_general(xml_str, 'product_blurb', get_product_description)

    def fix_stuff(self, xml_str):
        EMAIL_WIDTH = 600
        soup = BeautifulSoup(xml_str, 'xml')  # Using 'lxml-xml' parser to preserve xml structure.
        for img in soup.find_all('mj-image'):
            if 'width' in img.attrs:
                old_width_str = img['width']
                if old_width_str.endswith('%'):
                    old_width_percentage = float(old_width_str.rstrip('%'))  # Remove the '%' and convert to float
                    new_width = int(EMAIL_WIDTH * old_width_percentage / 100)  # Calculate absolute width relative to 600px
                    img['width'] = str(new_width)  # Update the 'width' attribute

        return str(soup)

    def build_mjml_head(self, font_list):
        head_str = "<mj-head>\n"
        font_template = '<mj-font name="{font_name}" href="{font_link}" />'
        for font in font_list:
            font_name = font[font.index(',')] if ',' in font else font
            font_link = get_google_font_link(font_name)
            head_str += font_template.format(font_name=font_name, font_link=font_link)
        head_str += "</mj-head>"
        return head_str

    def get_product_photo(self, description):
        return random.choice(self.product_photos)

    def get_page_photo(self, description):
        return random.choice(self.page_photos)
    
    def replace_company_name(self, url, xml_str):
        def get_company_name(url):
            if url == 'https://www.marble-lotus.com/':
                return "Marble Lotus"
            if url == 'https://threadandspoke.com/':
                return "Thread and Spoke"
        company_name = get_company_name(url)
        return xml_str.replace('$company_name$', company_name)
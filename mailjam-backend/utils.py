import os
from openai import OpenAI
import requests
import numpy as np
from joblib import Memory

# openai.api_key = os.getenv('OPENAI_API_KEY', 'not the token')

memory = Memory('./cachedir', verbose=0)

np.random.seed(1)

@memory.cache
def openai_query(query, json_mode=False):
    MODEL = 'gpt-4-1106-preview'
    TEMPERATURE = 0.0

    client = OpenAI()
    opt_dict = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "messages": [
            {"role": "user", "content": query}
        ],
    }

    if json_mode:
        opt_dict["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**opt_dict)

    return completion.choices[0].message.content

@memory.cache
def unsplash_search_query(query):
    url = 'https://api.unsplash.com/search/photos'
    params = {
        'query': query,
        'client_id': 'aUMTV92Q8VWaOBODACjluxA2_QFTfWtHXB_BCaP5yoo',
    }

    response = requests.get(url, params=params)

    # The response of the API can be accessed using response.json()
    return response.json()

def get_unsplash_url(query):
    query_results = unsplash_search_query(query)['results']
    idx = get_weighted_random(len(query_results) - 1)
    print(idx)
    return query_results[idx]['urls']['regular']

@memory.cache
def get_product_description(desc):
    prompt = f"""Based on the following description of a product, generate an enticing product blurb of around 20 words.

PRODUCT DESCRIPTION:
{desc}

BLURB:

"""
    return openai_query(prompt).strip()

prev_num = {"num": None}

def get_weighted_random(n, lambd=1.0):
    # Generate a random number from an exponential distribution
    r = np.random.exponential(1.0/lambd)
    
    # Scale the random number so it's between 0 and n
    r_scaled = r * n
    
    # Make sure it's within the bounds [0, n]
    r_clipped = min(max(0, r_scaled), n)
    
    return int(r_clipped)

def get_google_font_link(font_name):
    if font_name == 'Bauer Bodoni':
        return 'https://fonts.shopifycdn.com/bauer_bodoni/bauerbodoni_n7.6ba4277576da62f25b86b1485f3bf74f24b35351.woff2?h1=bWFyYmxlLWxvdHVzLWxsYy5hY2NvdW50Lm15c2hvcGlmeS5jb20&h2=bWFyYmxlLWxvdHVzLmNvbQ&hmac=1e7c48aae96049c535330230c6d972cf484b0fc10c6bdcce010750f4e6d6d8b3'
    elif font_name == 'Futura':
        return 'https://fonts.shopifycdn.com/futura/futura_n4.df36ce3d9db534a4d7947f4aa825495ed740e410.woff2?h1=bWFyYmxlLWxvdHVzLWxsYy5hY2NvdW50Lm15c2hvcGlmeS5jb20&h2=bWFyYmxlLWxvdHVzLmNvbQ&hmac=eaae3e608acb786c0250392718d6cc1fdcf16b7116f677dbedb2cad271aa4097'
    response = requests.get(f'https://fonts.googleapis.com/css2?family={font_name.replace(" ", "+")}')
    if response.status_code == 200:
        return f'https://fonts.googleapis.com/css2?family={font_name.replace(" ", "+")}'
    else:
        return None
    
def flatten_list(nested_list):
    return [item for sublist in nested_list for item in sublist]

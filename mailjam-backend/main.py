from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

from email_generator import EmailGenerator

app = Flask(__name__)
CORS(app)

@app.route('/gettemplate', methods=['GET'])
@cross_origin()
def get_template():
    data = request.args
    # query = data['query']
    url = data['url']

    # query = 'An email for an Italian luxury handbag store. Use valentines day colors, and write about how our bags would make the perfect gift'
    # query = 'A fathers day promo for a south asian goods decor brand'
    # query = 'An email for a jewelry store with a summery vibe, catalog of products midway down'
    # query = 'A marketing email for a men's watch store, use red and gray themes'
    # query = 'Winter themed marketing email for an Indian home decor webstore called "Marble Lotus"'
    # query = 'Marketing email for an Indian home decor webstore called "Marble Lotus"'
    query = 'Marketing email for an ecommerce store'
    mjml_res = EmailGenerator().generate(query, url)
    
    response = jsonify({"response": mjml_res})
    # response.headers.add('Access-Control-Allow-Origin', '*')
    print(response)
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105)

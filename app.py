import os
import json
import logging
from flask import Flask, render_template, request, jsonify

from utils import process_hex_string, get_example_hex_strings

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

@app.route('/')
def index():
    """Render the main page with the hex string input form."""
    example_hex_strings = get_example_hex_strings()
    return render_template('index.html', example_hex_strings=example_hex_strings)

@app.route('/parse', methods=['POST'])
def parse_hex():
    """Parse the submitted hex string and return the results."""
    data = request.get_json()
    
    if not data or 'hex_string' not in data:
        return jsonify({
            'success': False,
            'error': 'No hex string provided'
        }), 400
    
    hex_string = data['hex_string'].strip()
    tank_height = float(data.get('tank_height', 0.254))  # Default to 0.254m (20-lb tank)
    
    if not hex_string:
        return jsonify({
            'success': False,
            'error': 'Hex string cannot be empty'
        }), 400
    
    # Process the hex string
    result = process_hex_string(hex_string, tank_height)
    
    if not result:
        return jsonify({
            'success': False,
            'error': 'Failed to parse the hex string. Please check that it is a valid Mopeka sensor payload.'
        }), 400
    
    return jsonify({
        'success': True,
        'data': result
    })

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

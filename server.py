import secrets
import shutil
import sys, os, re
from flask import Flask, flash, request, redirect, render_template, session, send_from_directory
from werkzeug.utils import secure_filename

from binance import Binance_Converter
from bitcoin_de import BDE_Converter
from coinbase import Coinbase_Converter
from custom_conversion import Custom_Converter
from exchange import ExchangeCalculator

file_mb_max = 10
extensions = ['csv']
upload_dest = './uploads/'

app = Flask(__name__, static_url_path='/uploads/')
app.secret_key = secrets.token_urlsafe(16)
app.config['MAX_CONTENT_LENGTH'] = file_mb_max * 1024 * 1024

user_map = dict()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


def get_type_of_data(filename):
    with open(filename, 'r', newline='') as csvfile:
        first_line = csvfile.readline()
        if first_line.startswith('Datum;Typ;'):
            return 'bitcoin.de'
        elif first_line.startswith('Date(UTC);Pair;'):
            return 'binance'
        elif first_line.startswith('Timestamp,Transaction Type,'):
            return 'coinbase'
        elif first_line.startswith('Timestamp;Currency;'):
            return 'custom'
        else:
            return 'unknown'


def get_transactions_from_file(filename):
    data_type = get_type_of_data(filename)
    if data_type == 'bitcoin.de':
        return BDE_Converter(filename).process()
    elif data_type == 'binance':
        return Binance_Converter(filename).process()
    elif data_type == 'coinbase':
        return Coinbase_Converter(filename).process()
    elif data_type == 'custom':
        return Custom_Converter(filename).process()
    else:
        return []

@app.route('/report/<username>')
def report_per_user(username):
    directory = user_map[username]
    user_dir = os.path.join(upload_dest, directory)
    if os.path.isdir(user_dir):
        all_transactions = []
        for name in os.listdir(user_dir):
            fullname = os.path.join(user_dir, name)
            all_transactions += get_transactions_from_file(fullname)
        calc = ExchangeCalculator(all_transactions)
        calc.process_transactions()
        calc.calculate_totals_per_year()
        calc.render_html(user_dir)
        return send_from_directory(user_dir, 'report.html')

    return {'error': "Couldn't use uploaded data"}

@app.route('/crypto-upload/template.csv')
def send_upload_template():
    return send_from_directory('templates', 'data_template.csv')

## on page '/upload' load display the upload file
@app.route('/crypto-upload')
def upload_form():
    return send_from_directory('templates', 'upload.html')

@app.route('/crypto-upload', methods=['POST'])
def upload_file():
    random_user = secrets.token_hex(16)
    random_dir = secrets.token_hex(16)
    user_map[random_user] = random_dir
    dest_dir = os.path.join(upload_dest, random_dir)
    if not os.path.isdir(dest_dir):
        os.mkdir(dest_dir)
    if request.method == 'POST':
        if 'files[]' not in request.files:
            flash('No files found, try again.')
            return redirect(request.url)
        files = request.files.getlist('files[]')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(dest_dir, filename))
        flash('File(s) uploaded')
    return {'report': random_user}

#############################
# Additional Code Goes Here #
#############################

if __name__ == "__main__":
    shutil.rmtree(upload_dest)
    if not os.path.isdir(upload_dest):
        os.mkdir(upload_dest)
    app.run(host='0.0.0.0', port=4000, debug=False, threaded=True)
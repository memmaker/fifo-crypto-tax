import csv
from datetime import datetime
from decimal import Decimal

from config import config
from transaction import Transaction
import re

class Binance_Conversion_Converter:

    def __init__(self, path_to_csv):
        self.filename = path_to_csv
        self.currency_map = {
            'BTC': 'btc',
            'DOGEEUR': 'doge',
            'AVAXBTC': 'avax',
            'DOTBTC': 'dot',
            'BNBBTC': 'bnb',
            'ADABTC': 'ada',
        }

    def process(self):
        all_transactions = list()
        parse = lambda value: Decimal(re.sub('[a-zA-Z,]', '', value))
        with open(self.filename, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';', quotechar='"')
            for row in reader:
                if row['Type'] == 'Buy':
                    source_currency = config['fiat_currency']
                    target_currency = self.currency_map[row['Pair']]

                    source_amount = parse(row['Price'])
                    target_amount = parse(row['Amount'])
                    buy_tx = Transaction({
                        'timestamp':  datetime.strptime(row['Timestamp'], "%m/%d/%y %I:%M %p"),

                        'source_amount': source_amount,
                        'source_currency': source_currency,

                        'target_amount': target_amount,
                        'target_currency': target_currency,
                        'fees': parse(row['Fees']),

                        'reference': 'Binance Conversion'
                    })
                    all_transactions.append(buy_tx)
                elif row['Type'] == 'Sell':
                    source_currency = self.currency_map[row['Pair']]
                    target_currency = config['fiat_currency']

                    source_amount = parse(row['Amount'])
                    target_amount = parse(row['Price'])  # does not contain fees
                    sell_tx = Transaction({
                        'timestamp': datetime.strptime(row['Timestamp'], "%m/%d/%y %I:%M %p"),

                        'source_amount': source_amount,
                        'source_currency': source_currency,

                        'target_amount': target_amount,
                        'target_currency': target_currency,
                        'fees': parse(row['Fees']),

                        'reference': 'Binance Conversion'
                    })
                    all_transactions.append(sell_tx)
        return all_transactions


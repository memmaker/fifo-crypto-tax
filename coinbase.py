import csv
from datetime import datetime
from decimal import Decimal

from config import config
from transaction import Transaction

class Coinbase_Converter:

    def __init__(self, path_to_csv):
        self.filename = path_to_csv
        self.currency_map = {
            'BTC': 'btc',
            'ADA': 'ada',
            'SHIB': 'shib',
            'DOT': 'dot'
        }

    def process(self):
        all_transactions = list()
        with open(self.filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                if row['Transaction Type'] == 'Buy':
                    source_currency = config['fiat_currency']
                    target_currency = self.currency_map[row['Asset']]

                    source_amount = Decimal(row['Total (inclusive of fees)'])
                    target_amount = Decimal(row['Quantity Transacted'])
                    buy_tx = Transaction({
                        'timestamp':  datetime.strptime(row['Timestamp'], "%Y-%m-%dT%H:%M:%SZ"),

                        'source_amount': source_amount,
                        'source_currency': source_currency,

                        'target_amount': target_amount,
                        'target_currency': target_currency,
                        'fees': Decimal(row['Fees']),

                        'reference': 'Coinbase'
                    })
                    all_transactions.append(buy_tx)
                elif row['Transaction Type'] == 'Sell':
                    source_currency = self.currency_map[row['Asset']]
                    target_currency = config['fiat_currency']

                    source_amount = Decimal(row['Quantity Transacted'])
                    target_amount = Decimal(row['Total (inclusive of fees)'])  # does not contain fees

                    sell_tx = Transaction({
                        'timestamp': datetime.strptime(row['Timestamp'], "%Y-%m-%dT%H:%M:%SZ"),

                        'source_amount': source_amount,
                        'source_currency': source_currency,

                        'target_amount': target_amount,
                        'target_currency': target_currency,
                        'fees': Decimal(row['Fees']),

                        'reference': 'Coinbase'
                    })
                    all_transactions.append(sell_tx)
        return all_transactions


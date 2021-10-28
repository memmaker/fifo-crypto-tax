import csv
import datetime
from decimal import Decimal

from transaction import Transaction

class BDE_Converter:

    def __init__(self, path_to_csv):
        self.filename = path_to_csv
        self.currency_map = {
            'BTC': 'btc',
            'ETH': 'eth'
        }
    def process(self):
        all_transactions = list()
        with open(self.filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';', quotechar='"')
            for row in reader:
                currency = row['Währung']
                if row['Typ'] == 'Kauf':
                    source_currency = 'euro'
                    target_currency = self.currency_map[currency]

                    source_amount = Decimal(row['Menge vor Gebühr'])
                    target_amount = Decimal(row['%s nach Bitcoin.de-Gebühr' % currency])
                    amount_before_fee = Decimal(row['%s vor Gebühr' % currency])
                    fee_target_currency = amount_before_fee - target_amount
                    exchange_rate = Decimal(row['Kurs'])
                    fees = fee_target_currency * exchange_rate
                    buy_tx = Transaction({
                        'timestamp':  datetime.datetime.strptime(row['Datum'], '%Y-%m-%d %H:%M:%S'),

                        'source_amount': source_amount,
                        'source_currency': source_currency,

                        'target_amount': target_amount,
                        'target_currency': target_currency,
                        'fees': fees,

                        'reference': "Bitcoin.de (%s)" % row['Referenz']
                    })
                    all_transactions.append(buy_tx)
                elif row['Typ'] == 'Verkauf':
                    source_currency = self.currency_map[currency]
                    target_currency = 'euro'

                    source_amount = Decimal(row['%s vor Gebühr' % currency])
                    target_amount = Decimal(row['Menge nach Bitcoin.de-Gebühr'])  # does not contain fees
                    amount_before_fee = Decimal(row['Menge vor Gebühr'])
                    fees = amount_before_fee - target_amount

                    sell_tx = Transaction({
                        'timestamp': datetime.datetime.strptime(row['Datum'], '%Y-%m-%d %H:%M:%S'),

                        'source_amount': source_amount,
                        'source_currency': source_currency,

                        'target_amount': target_amount,
                        'target_currency': target_currency,
                        'fees': fees,

                        'reference': "Bitcoin.de (%s)" % row['Referenz']
                    })
                    all_transactions.append(sell_tx)
        return all_transactions


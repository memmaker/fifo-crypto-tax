import csv
import datetime
from decimal import Decimal

from config import config
from transaction import Transaction, ExternalTransaction


class BDE_Converter:

    def __init__(self, path_to_csv):
        self.filename = path_to_csv
    def process(self):
        all_transactions = list()
        with open(self.filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';', quotechar='"')
            for row in reader:
                currency = row['Währung']
                if row['Typ'] == 'Kauf':
                    source_currency = config['fiat_currency']
                    target_currency = currency

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
                    source_currency = currency
                    target_currency = config['fiat_currency']

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
                elif row['Typ'] in ['Einzahlung', 'Auszahlung', 'Netzwerk-Gebühr']:
                    change_amount = Decimal(row['Zu- / Abgang'])
                    reference = "Bitcoin.de (%s…)" % row['Referenz'][:6]
                    timestamp = datetime.datetime.strptime(row['Datum'], '%Y-%m-%d %H:%M:%S')
                    all_transactions.append(ExternalTransaction(timestamp, currency, change_amount, reference))
        return all_transactions


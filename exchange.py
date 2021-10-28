import os
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from binance import Binance_Converter
from bitcoin_de import BDE_Converter
from coinbase import Coinbase_Converter
from config import config
from transaction import Transaction, c, remove_exponent, ExternalTransaction
from genshi.template import TemplateLoader
from enum import Enum

class TaxType(Enum):
    Kauf = 0
    Verk = 1
    Ext = 3

def ensure_key(map, date_of_record):
    year = date_of_record.year
    if year not in map:
        map[year] = list()

class TransactionWithTaxInfo:
    def __init__(self, tax_id, type, timestamp, currency, win_or_loss, exchange_rate, fiat_amount, crypto_amount, reference, fees, source_transaction):
        self.tax_id = tax_id
        self.win_or_loss = win_or_loss
        self.fees = fees
        self.source_transaction = source_transaction
        self.reference = reference
        self.crypto_amount = crypto_amount
        self.fiat_amount = fiat_amount
        self.type = type
        self.exchange_rate = exchange_rate
        self.timestamp = timestamp
        self.currency = currency
        self.display_id = self.type.name + '-' + str(self.tax_id)
        self.long_time = False
        self.source_id = self.source_transaction.display_id if self.source_transaction else "n/a"
        if type == TaxType.Verk:
            one_year = relativedelta(years=1)
            threshold = self.timestamp - one_year
            if source_transaction.timestamp <= threshold:
                self.long_time = True
        self.display_class = 'no-tax' if self.long_time else 'normal'

class Account:
    def __init__(self, name, initial_funding=0.0):
        self.name = name
        self.initial_funding = Decimal(initial_funding)
        self.external_balance = Decimal(0.0)
        self.balance = Decimal(0.0)

    def add_funds(self, amount, tx_id):
        self.balance += amount

    def remove_funds(self, amount):
        self.balance -= amount
        return False

    def info(self):
        return "%s: %s" % (self.name, self.balance)

    def snapshot(self):
        return (self.name, self.balance)

    def track_external_transfer(self, change):
        self.external_balance += change

    def corrected_balance(self):
        return self.initial_funding + self.external_balance + self.balance

class FifoAccount(Account):
    def __init__(self, name, initial_funding=0.0):
        self.queue_of_funds = list()
        super().__init__(name, initial_funding=0.0)

    def add_funds(self, amount, tx_id):
        self.queue_of_funds.insert(0, (amount, tx_id))
        super().add_funds(amount, tx_id)

    def remove_funds(self, amount):
        amount_to_remove = amount
        results = list()
        while amount_to_remove > 0:
            last_item = self.queue_of_funds.pop()
            funds_of_last_item = last_item[0]
            tx_id_of_last_item = last_item[1]
            if funds_of_last_item >= amount_to_remove:
                # we only need to touch this one
                funds_of_last_item -= amount_to_remove
                if funds_of_last_item > 0.0:
                    self.queue_of_funds.append((funds_of_last_item, tx_id_of_last_item))
                results.append((amount_to_remove, tx_id_of_last_item))
                amount_to_remove = 0
            else:
                amount_to_remove -= funds_of_last_item
                results.append(last_item)
        super().remove_funds(amount)
        return results


class ExchangeCalculator:
    def __init__(self, transactions):
        self.snapshots = dict()
        self.fiat_currency = config['fiat_currency']
        self.transactions = dict()
        self.tax_relevant = dict()
        self.buy_map = dict()
        self.totals = dict()
        sortkey = lambda tx: tx.timestamp
        index = 0
        for tx in sorted(transactions, key=sortkey):
            self.transactions[index] = tx
            index += 1
        self.accounts = {
            self.fiat_currency: Account(self.fiat_currency)
        }

    def show_accounts(self):
        print("\n**** ACCOUNTS ****")
        for name, acc in self.accounts.items():
            print(acc.info())

    def render_html(self, output_dir):
        loader = TemplateLoader(
            os.path.join(os.path.dirname(__file__), 'templates'),
            auto_reload=True
        )
        tmpl = loader.load('tax_report.html')
        html_output = tmpl.generate(accounts=self.snapshots, tax_relevant=self.tax_relevant, totals=self.totals, c=c, fc=remove_exponent).render('html', doctype='html')

        with open(os.path.join(output_dir, "report.html"), "w") as file:
            file.write(html_output)

    def calculate_totals_per_year(self):
        for year, transactions in self.tax_relevant.items():
            fees = Decimal(0.0)
            wins_losses = Decimal(0.0)
            for tx in transactions:
                fees += tx.fees
                if not tx.long_time or tx.win_or_loss < 0:
                    wins_losses += tx.win_or_loss
            if not year in self.totals:
                self.totals[year] = dict()
            self.totals[year]['fees'] = fees
            self.totals[year]['wins_losses'] = wins_losses

    # requires every transaction to have the fiat currency in the target or source field
    def process_transactions(self):
        sell_tax_id = 0
        buy_tax_id = 0
        external_id = 0
        current_transaction_year = 0
        self.snapshot_accounts(current_transaction_year)

        for tx_id, tx in self.transactions.items():

            tx_year = tx.timestamp.year
            if tx_year != current_transaction_year:
                self.snapshot_accounts(current_transaction_year)
                current_transaction_year = tx_year

            if isinstance(tx, ExternalTransaction):
                currency = tx.currency
                if currency not in self.accounts:
                    self.accounts[currency] = FifoAccount(currency)
                change = tx.change_amount
                if change < Decimal(0):
                    self.accounts[currency].track_external_transfer(change)
                    external_tax_tx = TransactionWithTaxInfo(external_id, TaxType.Ext, tx.timestamp, tx.currency,
                                                             Decimal(0), Decimal(0), Decimal(0),
                                                             change, tx.reference, Decimal(0), None)
                    self.tax_relevant[tx.timestamp.year].append(external_tax_tx)
                    external_id += 1
                else:
                    external_tax_tx = TransactionWithTaxInfo(external_id, TaxType.Ext, tx.timestamp, tx.currency,
                                                        Decimal(0), Decimal(0), Decimal(0),
                                                        change, tx.reference, Decimal(0), None)
                    self.accounts[currency].track_external_transfer(change)
                    self.tax_relevant[tx.timestamp.year].append(external_tax_tx)
                    external_id += 1
                continue

            list_of_buy_transactions = []
            if tx.source_currency not in self.accounts:
                self.accounts[tx.source_currency] = FifoAccount(tx.source_currency)
            src_account = self.accounts[tx.source_currency]
            is_sell = False
            try:
                list_of_buy_transactions = src_account.remove_funds(tx.source_amount)
                is_sell = tx.target_currency == self.fiat_currency and list_of_buy_transactions
            except IndexError as e:
                print('ERR with tx: %s' % tx.info())
                print('..tried to remove %s from empty account %s' % (tx.source_amount, src_account.info()))
            if tx.target_currency not in self.accounts:
                self.accounts[tx.target_currency] = FifoAccount(tx.target_currency)
            trg_account = self.accounts[tx.target_currency]
            trg_account.add_funds(tx.target_amount, buy_tax_id)
            is_buy = not is_sell and tx.source_currency == self.fiat_currency

            if is_sell:
                # this is sell back to fiat with wins or lossess and thus tax relevant
                ensure_key(self.tax_relevant, tx.timestamp)

                for pair in list_of_buy_transactions:
                    amount_of_tx = pair[0]
                    buy_tx_id = pair[1]
                    buy_tx = self.buy_map[buy_tx_id]

                    buy_price = amount_of_tx * buy_tx.exchange_rate
                    sell_price = amount_of_tx * tx.exchange_rate

                    delta_amount = sell_price - buy_price
                    tax_tx = TransactionWithTaxInfo(sell_tax_id, TaxType.Verk, tx.timestamp, tx.source_currency, delta_amount,
                                                    tx.exchange_rate,
                                                    sell_price, amount_of_tx, tx.reference, tx.fees,
                                                    buy_tx)
                    self.tax_relevant[tx.timestamp.year].append(tax_tx)
                    sell_tax_id += 1
            elif is_buy:
                ensure_key(self.tax_relevant, tx.timestamp)
                buy_tax_tx = TransactionWithTaxInfo(buy_tax_id, TaxType.Kauf, tx.timestamp, tx.target_currency, Decimal(0), tx.exchange_rate, tx.source_amount, tx.target_amount, tx.reference, tx.fees, None)
                self.tax_relevant[tx.timestamp.year].append(buy_tax_tx)
                self.buy_map[buy_tax_id] = buy_tax_tx
                buy_tax_id += 1
            else:
                print('WARNING! Skipping: %s' % tx.info())

        self.snapshot_accounts(current_transaction_year)

    def snapshot_accounts(self, year):
        if year not in self.snapshots:
            self.snapshots[year] = dict()
        for name, acc in self.accounts.items():
            if acc.name == config['fiat_currency']:
                self.snapshots[year][acc.name] = c(acc.corrected_balance())
            else:
                self.snapshots[year][acc.name] = acc.corrected_balance().normalize()


if __name__ == "__main__":

    print('reading bitcoin.de')
    bitcoin_de_btc_transactions = BDE_Converter('./data/btc_account_statement_extended_20150101-20211027.csv').process()
    bitcoin_de_eth_transactions = BDE_Converter('./data/eth_account_statement_extended_20150101-20211027.csv').process()
    print('reading coinbase')
    coinbase_transactions = Coinbase_Converter('./data/Coinbase-until-2021-10-27.csv').process()
    print('reading binance')
    binance_transactions = Binance_Converter('./data/binance_2021-04-01_2021-10-27.csv').process()
    print('reading binance conversions')
    #binance_conversions = Binance_Conversion_Converter('./data/binance_conversions.csv').process()

    tx_list = bitcoin_de_btc_transactions \
              + bitcoin_de_eth_transactions \
              + coinbase_transactions \
              + binance_transactions
    #bnb_txs = list(filter(lambda x: x.source_currency == 'bnb' or x.target_currency == 'bnb', tx_list))
    #two_years = relativedelta(years=3)
    #threshold = datetime.datetime.now() - two_years
    #last_two_years = lambda x: x.timestamp >= threshold

    #txs_last_two_years = list(filter(last_two_years, tx_list))

    calc = ExchangeCalculator(tx_list)
    calc.process_transactions()
    calc.calculate_totals_per_year()
    calc.render_html()
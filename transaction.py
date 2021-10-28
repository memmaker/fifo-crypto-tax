from decimal import Decimal

from config import config

def remove_exponent(d):
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()

def moneyfmt(value, places=2, curr='', sep='.', dp=',',
             pos='', neg='-', trailneg=''):
    """Convert Decimal to a money formatted string.

    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    pos:     optional sign for positive numbers: '+', space or blank
    neg:     optional sign for negative numbers: '-', '(', space or blank
    trailneg:optional trailing minus indicator:  '-', ')', space or blank

    >>> d = Decimal('-1234567.8901')
    >>> moneyfmt(d, curr='$')
    '-$1,234,567.89'
    >>> moneyfmt(d, places=0, sep='.', dp='', neg='', trailneg='-')
    '1.234.568-'
    >>> moneyfmt(d, curr='$', neg='(', trailneg=')')
    '($1,234,567.89)'
    >>> moneyfmt(Decimal(123456789), sep=' ')
    '123 456 789.00'
    >>> moneyfmt(Decimal('-0.02'), neg='<', trailneg='>')
    '<0.02>'

    """
    q = Decimal(10) ** -places      # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q).as_tuple()
    result = []
    digits = list(map(str, digits))
    build, next = result.append, digits.pop
    if sign:
        build(trailneg)
    for i in range(places):
        build(next() if digits else '0')
    if places:
        build(dp)
    if not digits:
        build('0')
    i = 0
    while digits:
        build(next())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    build(curr)
    build(neg if sign else pos)
    return ''.join(reversed(result))

class ExternalTransaction:
    def __init__(self, timestamp, currency, change_amount, reference):
        self.timestamp = timestamp
        self.reference = reference
        self.change_amount = change_amount
        self.currency = currency

class Transaction:
    def __init__(self, tx_data):
        self.timestamp = tx_data['timestamp']
        self.source_currency = tx_data['source_currency']
        self.target_currency = tx_data['target_currency']
        self.source_amount = tx_data['source_amount']  # without fees
        self.target_amount = tx_data['target_amount']  # without fees
        self.fees = tx_data['fees']
        self.reference = tx_data['reference']
        if self.source_currency == config['fiat_currency']:
            self.exchange_rate = self.source_amount / self.target_amount
        elif self.target_currency == config['fiat_currency']:
            self.exchange_rate = self.target_amount / self.source_amount

    def info(self):
        return "%s: %s %s -> %s %s @ %s (fees: %s, ref: %s)" % (self.timestamp, self.source_amount, self.source_currency, self.target_amount, self.target_currency, self.exchange_rate, c(self.fees), self.reference)

c = moneyfmt

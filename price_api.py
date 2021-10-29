import requests

# accepts "EUR"
# get_price_of_currency(datetime, "BTC", "EUR", "CCCAGG")
# returns btc price at timestamp
def get_price_of_currency(date, src_currency, dst_currency="EUR", exchange_name="CCCAGG"):
    api_key = 'fdd5567533e48983c76eb58ebce59dbb1a3c19f3597e4ea316b2c4ab3a4f31f8'
    if src_currency == 'XBT':
        src_currency = 'BTC'
    if dst_currency == 'XBT':
        dst_currency = 'BTC'
    url = 'https://min-api.cryptocompare.com/data/v2/histohour?toTs=' \
          + date.strftime('%s') \
          + '&e=' + exchange_name \
          + '&fsym=' + src_currency \
          + '&tsym=' + dst_currency \
          + '&limit=1&api_key=' + api_key
    try:
        data = requests.get(url).json()['Data']['Data']
        price = (float(data[0]['close']) + float(data[1]['close'])) / 2
        return price
    except:
        print('API unsuccessfully!')
        return False



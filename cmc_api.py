from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json

url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical'
parameters = {
  'id':'1839', # binance coin
  'time_start':'2019-01-01T00:00:00Z',
  'time_end':'2021-10-27T23:59:59Z',
  'interval':'15m',
  'convert':'EUR'
}
headers = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': '183fb68a-929a-4c9f-89f5-99c7bb01ff8b',
}

session = Session()
session.headers.update(headers)

try:
  response = session.get(url, params=parameters)
  data = json.loads(response.text)
  print(data)
except (ConnectionError, Timeout, TooManyRedirects) as e:
  print(e)
import requests
import json
import sqlite3
import os
from config import *
import requests
import json
import sqlite3
import os
from config import *


# 1. fetch old price data if its there, else create an empty db 
if not os.path.isfile(f"system.db"):
    # create an empty db 
    conn = sqlite3.connect('system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE ratepairs
             (id integer primary key, ratepair text, price real)''')
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('BTCBTC', 1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('BTCUSD', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('BTCINR', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('USDINR', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('FLOUSD', -1)")
    conn.commit()
    conn.close()

# load old price data 
# load older price data
conn = sqlite3.connect('system.db')
c = conn.cursor()
ratepairs = c.execute('select ratepair, price from ratepairs')
ratepairs = ratepairs.fetchall()
prices = {}

for ratepair in ratepairs:
    ratepair = list(ratepair)
    prices[ratepair[0]] = ratepair[1]
    


# 2. fetch new price data

# apilayer
response = requests.get(
    f"http://apilayer.net/api/live?access_key={apilayerAccesskey}")
try:
    price = response.json()
    prices['USDINR'] = price['quotes']['USDINR']
except ValueError:
    print('Json parse error')    


# bitpay
response = requests.get('https://bitpay.com/api/rates')
try:
    bitcoinRates = response.json()
    for currency in bitcoinRates:
        if currency['code'] == 'USD':
            prices['BTCUSD'] = currency['rate']
        elif currency['code'] == 'INR':
            prices['BTCINR'] = currency['rate']
except ValueError:
    # coindesk
    response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
    try:
        price = response.json()
        prices['BTCUSD'] = price['bpi']['USD']['rate']
    except ValueError:
        print('Json parse error')


# cryptocompare 
response = requests.get('https://min-api.cryptocompare.com/data/histoday?fsym=FLO&tsym=USD&limit=1&aggregate=3&e=CCCAGG')
try:
    price = response.json()
    prices['FLOUSD'] = price['Data'][-1]['close']
except ValueError:
    print('Json parse error')    



# 3. update latest price data
print('\n\n')
print(prices)

conn = sqlite3.connect('system.db')
c = conn.cursor()
for pair in list(prices.items()):
    pair = list(pair)
    c.execute(f"UPDATE ratepairs SET price={pair[1]} WHERE ratepair='{pair[0]}'")
conn.commit()




    
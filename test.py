import time
import dateparser
import pytz
import json

from datetime import datetime
from binance.client import Client
from pushover import init, Client as pushoverClient

def date_to_milliseconds(date_str):

    # get epoch value in UTC
    epoch = datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    # parse our date string
    d = dateparser.parse(date_str)
    # if the date is not timezone aware apply UTC timezone
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d = d.replace(tzinfo=pytz.utc)

    # return the difference in time
    return int((d - epoch).total_seconds() * 1000.0)


def interval_to_milliseconds(interval):
    """Convert a Binance interval string to milliseconds

    :param interval: Binance interval string 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
    :type interval: str

    :return:
         None if unit not one of m, h, d or w
         None if string not in correct format
         int value of interval in milliseconds
    """
    ms = None
    seconds_per_unit = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60
    }

    unit = interval[-1]
    if unit in seconds_per_unit:
        try:
            ms = int(interval[:-1]) * seconds_per_unit[unit] * 1000
        except ValueError:
            pass
    return ms


def get_historical_klines(symbol, interval, start_str, end_str=None):

    # create the Binance client, no need for api key
    client = Client("", "")

    # init our list
    output_data = []

    # setup the max limit
    limit = 500

    # convert interval to useful value in seconds
    timeframe = interval_to_milliseconds(interval)

    # convert our date strings to milliseconds
    start_ts = date_to_milliseconds(start_str)
    # if an end time was passed convert it
    end_ts = None
    if end_str:
        end_ts = date_to_milliseconds(end_str)

    idx = 0
    # it can be difficult to know when a symbol was listed on Binance so allow start time to be before list date
    symbol_existed = False
    while True:
        # fetch the klines from start_ts up to max 500 entries or the end_ts if set
        temp_data = client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
            startTime=start_ts,
            endTime=end_ts
        )

        # handle the case where our start date is before the symbol pair listed on Binance
        if not symbol_existed and len(temp_data):
            symbol_existed = True

        if symbol_existed:
            # append this loops data to our output data
            output_data += temp_data

            # update our start timestamp using the last value in the array and add the interval timeframe
            start_ts = temp_data[len(temp_data) - 1][0] + timeframe
        else:
            # it wasn't listed yet, increment our start date
            start_ts += timeframe

        idx += 1
        # check if we received less than the required limit and exit the loop
        if len(temp_data) < limit:
            # exit the while loop
            break

        # sleep after every 3rd call to be kind to the API
        if idx % 3 == 0:
            time.sleep(1)

    return output_data

def getGrowthRate(high, low):
    return format(((float(high) - float(low)) / float(low)) * 100, "2f")

currencyFile = open("tempCurrencies.txt")

def getNextCurrency():
    return currencyFile.readline()[:-1]

def isCurrencyTrending(klines, threshold):
    return float(klines[len(klines)-1][9]) > threshold

"""
[
    [
        1499040000000,      # Open time
        "0.01634790",       # Open
        "0.80000000",       # High
        "0.01575800",       # Low
        "0.01577100",       # Close
        "148976.11427815",  # Volume
        1499644799999,      # Close time
        "2434.19055334",    # Quote asset volume
        308,                # Number of trades
        "1756.87402397",    # Taker buy base asset volume
        "28.46694368",      # Taker buy quote asset volume
        "17928899.62484339" # Can be ignored
    ]
]
"""

init(PUSHOVER_API_TOKEN)
doRunContinue = True
doSendPushover = True
baseCurrency = "ETH"
while doRunContinue:
    symbol = getNextCurrency() + baseCurrency
    # doRunContinue = False
    # symbol = "BCDBTC"
    if(symbol == None or symbol == baseCurrency):
        currencyFile.seek(0)
        continue

    start = "5 minutes ago JST"
    interval = Client.KLINE_INTERVAL_1MINUTE

    klines = get_historical_klines(symbol, interval, start)

    growth = getGrowthRate(klines[len(klines)-1][2], klines[0][3])
    totalVolume = int(klines[len(klines)-1][5].split(".")[0])
    lastTredingVolume = klines[len(klines)-1][9]
    # if(isCurrencyTrending(klines, 500)):
    #     print(symbol[:-3])

    if (float(growth) > 0.001) and int(totalVolume) > 499 and float(lastTredingVolume) > 0:
        print(symbol[:-3] + "    " + str(growth) + "             " + str(lastTredingVolume.split(".")[0]))

        if doSendPushover and (float(growth) > 1.75):
            pushoverClient(PUSHOVER_USER_KEY).send_message(str(growth), title=symbol[:-3])
    # for i in klines:
    #     x = dateparser.parse(str(i[0]))
    #     print(str(x))

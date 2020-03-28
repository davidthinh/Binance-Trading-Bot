from TradingBot import TradingBot
from binance.client import Client

if __name__ == '__main__':
    """
    Website link: https://www.binance.us/en/trade/BTC_USD
    
    You can use the link above to compare the calculations of the bot with the stochastic rsi and 
    bollinger band values from the website. Make sure when comparing values match what the bot is using
    below.
    
    You can choose to keep the below what is currently or change it to values and assets you would like to see.
    I will give a brief description of what each value does in the README file to keep this code form being cluttered
    
    This script will initialize a new TradingBot object and run backtest. Backtest calculates all stochastic rsi and 
    bollinger band values while also calling the buy_sell function within trading bot. The buy_sell function will print 
    in console buy and sell order values. When the program ends a plot will show with where all buy and sell orders took 
    place. This trading bot trades under the assumption that the "limit orders" are executed immediately when placed. 
    A pseudo profit will also be printed in console. The profit takes into account the generic binance trading fee of 0.01%.
    
    *Note: it will only place a sell order if it has bought 
    """

    #Api information from throwaway account
    api_key = 'Ax3FFLo3sz07ClCOVBXFFojdnENbWZrjJrvjamdcaXkzb5Ei7RITYU2a69OqJHKp'
    api_secret = 'NXr7OGDAbCnc4r9hht1Q2HVVsF4wbgiPoINQDjePMLCC3D8j9kfGcs9D8qJjoiDJ'

    args = {
        #Stochastic RSI Attributes
        'rsi_period' : 14,
        'stochastic_period' : 9,
        'k_slow_period' : 3,
        'd_slow_period' : 3,

        #Bollinger Band Attributes
        'simple_moving_average_period' : 21,
        'bollinger_band_standard_deviation' : 2,

        #Buy and Sell Attributes
        'pair' : 'BTCUSD',
        'stochastic_upper_band' : 80,
        'stochastic_lower_band' : 20,
        'time_look_back' : '1 month ago UTC',
        'asset_interval' : Client.KLINE_INTERVAL_5MINUTE,
        'show_times' : 500
    }


    bot = TradingBot(api_key, api_secret, args)
    bot.backtest()


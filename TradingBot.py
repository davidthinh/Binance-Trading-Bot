from binance.client import Client
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as plt_dates
import datetime as dt

class TradingBot:

    def __init__(self, api_key, api_secret, args):

        #Bot information
        self.client = Client(api_key, api_secret)

        #Stoch RSI Information
        self.avg_gain, self.avg_loss = 0, 0
        self.rsi,  self.rsi_array = 0, []
        self.rsi_period, self.stoch_period = args['rsi_period'], args['stochastic_period']
        self.k_slow_period, self.d_slow_period = args['k_slow_period'], args['d_slow_period']
        self.k_fast_array, self.k_slow_array, self.d_slow_array = {'time':[],'k_fast':[]}, {'time':[],'k_slow':[]}, {'time':[],'d_slow':[]}
        self.stoch_lower, self.stoch_upper = args['stochastic_upper_band'], args['stochastic_lower_band']

        #Bollinger Band Information
        self.sma_period, self.sma_array = args['simple_moving_average_period'], []
        self.deviation = args['bollinger_band_standard_deviation']
        self.bb = {'time':[],'sma': [],'lower_band': [],'upper_band': []}

        #Buy Sell Algorithm Information
        self.orders = {'time':[],'order_limit': [],'order_type': []}
        self.time_look_back = args['time_look_back']
        self.asset_interval = args['asset_interval']
        self.status = 0
        self.buy_quantity = 0.002

        #Binance trading fees and general information
        self.pair = args['pair']
        self.show_times = args['show_times']
        self.closing_price_array, self.closing_times = [], []
        self.checked_prices, self.checked_times = [], []
        self.general_trade_fee = 0.001 # 0.1% trading fee Maker/Taker --> Seller/Buyer

    @staticmethod
    def simple_moving_average(arr, period):
        """Simple_moving_average = (A1+A2+...Ai)/i
        :param arr: An array of numeric values
        :param period: Number of numeric values in arr
        :return: simple moving average
        """
        return np.sum(arr) / period

    @staticmethod
    def wilders_moving_average(period, close, prev_moving_average):
        """
        :param period: Number of numeric values in arr
        :param close: The current closing price
        :param prev_moving_average: The previous moving average
        :return: wilders moving average
        """
        return ((prev_moving_average * (period - 1)) + close) / period

    @staticmethod
    def rsi_calc(avg_gain, avg_loss):
        """Calculates single rsi value
        :param avg_gain: The moving average of the sum of positive price changes over a period n
        :param avg_loss: The moving average of the sum of abs(negative) price changes over a period n
        :return: rsi value
        """

        rs = avg_gain / (avg_loss + 0.00000001)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def k_fast_stoch(rsi_array):
        """Calculates the k_fast value for stochastic indicator
        :param rsi_array: an array of stoch_period number of rsi values
        :return: k_fast value
        """
        close = rsi_array[len(rsi_array) - 1]
        high = np.amax(rsi_array)
        low = np.amin(rsi_array)
        return abs(((close - low) / (high - low))) * 100

    def bollinger_bands(self, kline_array, sma_period, deviation_number, time):
        """Calculates the values for the bollinger band indicator
        :param kline_array:
        :param sma_period: The period for the simple_moving_average
        :param deviation_number: The number of standard deviations away the upper and lower bands are from the sma
        :param time: The time when this value is calculated
        :return: simple_moving_average, bb upper band, bb lower band, deviation value
        """

        recent_numbers = kline_array[len(kline_array) - sma_period:]
        sma = self.simple_moving_average(sum(recent_numbers), sma_period)
        self.bb['sma'].append(sma)
        squared_errors = []
        for x in range(0, len(recent_numbers)):
            squared_errors.append(pow(recent_numbers[x] - sma, 2))
        standard_deviation = (sum(squared_errors) / len(squared_errors)) ** (1 / 2)
        upper_band = sma + standard_deviation * deviation_number
        lower_band = sma - standard_deviation * deviation_number
        self.bb['lower_band'].append(lower_band)
        self.bb['upper_band'].append(upper_band)
        self.bb['time'].append(time)
        return sma, upper_band, lower_band, standard_deviation

    def print_values(self):
        """Displays the current values for each indicator in the terminal
        :return: Nothing
        """
        print('Previous Stoch_RSI(%K_FAST)', self.k_fast_array['k_fast'][-1])
        print('Previous Stoch_RSI(%K_SLOW)', self.k_slow_array['k_slow'][-1])
        print('Previous Stoch_RSI(%D_SLOW)', self.d_slow_array['d_slow'][-1])
        print('RSI(Smoothed) ', self.rsi)
        print('Bollinger Lower Band', self.bb['lower_band'][-1])
        print('Bollinger Upper Band', self.bb['upper_band'][-1])
        print('Simple Moving Average', self.bb['sma'][-1], '\n')

    def backtest(self):
        """
        Calculates all stochastic rsi and bollinger band values up to the previous closing price. This is because
        the value for the current closing price usually is not completed.
        :param pair: The crypto pair the bot back tests with EX: 'BTCUSD' or 'ETHUSD'
        :return: Nothing
        """
        # Cut off most recent history closing price since it is not complete and would effect the calculations
        #kline_array = self.client.get_historical_klines(symbol=pair, interval=Client.KLINE_INTERVAL_5MINUTE, start_str= '1' + ' month ago UTC')
        kline_array = self.client.get_historical_klines(symbol=self.pair, interval=self.asset_interval, start_str= self.time_look_back)
        self.closing_times = [dt.datetime.utcfromtimestamp(x[6]/1000) for x in kline_array][0:-1]
        self.closing_price_array = [float(x[4]) for x in kline_array][0:-1]
        self.checked_prices = []

        gain, loss = 0, 0
        for x in range(0, len(self.closing_price_array)-1):
            change = self.closing_price_array[x+1] - self.closing_price_array[x]
            self.checked_prices.append(self.closing_price_array[x+1])
            self.checked_times.append(self.closing_times[x+1])
            if change > 0:
                gain += change
            elif change < 0:
                loss += abs(change)

            #Get first rsi simple moving average
            if x == self.rsi_period:
                self.avg_gain = self.simple_moving_average(gain, self.rsi_period)
                self.avg_loss = self.simple_moving_average(loss, self.rsi_period)
                self.rsi = self.rsi_calc(self.avg_gain, self.avg_loss)
                self.rsi_array.append(self.rsi)
                gain, loss = 0, 0

            #Use wilders moving average to continue calculating rsi values
            elif x > self.rsi_period:
                self.avg_gain = self.wilders_moving_average(self.rsi_period, gain, self.avg_gain)
                self.avg_loss = self.wilders_moving_average(self.rsi_period, loss, self.avg_loss)
                self.rsi = self.rsi_calc(self.avg_gain, self.avg_loss)
                self.rsi_array.append(self.rsi)
                gain, loss = 0, 0

                # When there are enough rsi values begin to calculate stoch_rsi
                if len(self.rsi_array) >= self.stoch_period:
                    k_fast = self.k_fast_stoch(self.rsi_array[len(self.rsi_array) - self.stoch_period:])
                    self.k_fast_array['k_fast'].append(k_fast)
                    self.k_fast_array['time'].append(self.closing_times[x])

                    # When there are enough %K_FAST values begin to calculate %K_SLOW values = sma of n %K_FAST values
                    if len(self.k_fast_array['k_fast']) >= self.k_slow_period:
                        k_slow = self.simple_moving_average(self.k_fast_array['k_fast'][-1*self.k_slow_period:], self.k_slow_period)
                        self.k_slow_array['k_slow'].append(k_slow)
                        self.k_slow_array['time'].append(self.closing_times[x])

                        # When there are enough %K_SLOW values begin to calculate %D_SLOW values = sma of n %K_SLOW values
                        if len(self.k_slow_array['k_slow']) >= self.d_slow_period:
                            d_slow = self.simple_moving_average(self.k_slow_array['k_slow'][-1*self.d_slow_period:], self.d_slow_period)
                            self.d_slow_array['d_slow'].append(d_slow)
                            self.d_slow_array['time'].append(self.closing_times[x])

                            self.bollinger_bands(self.checked_prices, self.sma_period, self.deviation, self.checked_times[x])

                            #Once all values start to be calculated we can determine whether to buy or sell until we hit the last
                            self.buy_sell(current_time = self.checked_times[x])

        self.plot_orders() #Plot orders on graph

    def buy_sell(self, current_time):
        """
        Lets user know when pseudo buy and sell orders are taken place along with the values of the indicators at those times.
        These orders would be limit orders and this functions assumes that the orders are executed immediately.
        :param current_time: The current time of the currently used closing price
        :return: Nothing
        """
        # Setting buy limit conditional
        next_price = self.checked_prices[-1]
        if self.k_slow_array['k_slow'][-1] <= self.stoch_lower and self.d_slow_array['d_slow'][-1] <= self.stoch_lower and next_price <= self.bb['lower_band'][-1] and self.status == 0:
            self.status = 1
            """
            Explaining conditional above:
            If both k_slow and d_slow value are lower than the users indicated lower bound on the stochastic rsi indicator, 
            the next price is below the lower band of the bollinger band indicator and there is no current order status 
            place a limit buy for desired asset quantity at the lower bollinger band value
            """
            #current_time_utc = dt.datetime.utcfromtimestamp(current_time/1000) #Binance timestamp is in ms, must / by 1000 to get seconds
            print('Current Price: ', next_price, '\nCreated Buy Order: ', self.bb['lower_band'][-1], '\nQuantity: ', self.buy_quantity, '\nTime: ', current_time)
            self.orders['time'].append(current_time)
            self.orders['order_limit'].append(self.bb['lower_band'][-1])
            self.orders['order_type'].append('buy')
            self.print_values()

        # Setting sell limit conditional
        elif self.k_slow_array['k_slow'][-1] >= self.stoch_upper and self.d_slow_array['d_slow'][-1] >= self.stoch_upper and next_price >= self.bb['upper_band'][-1] and self.status == 1:
            self.status = 0
            """
            Explaining conditional above:
            If both k_slow and d_slow value are higher than the users indicated upper bound on the stochastic rsi indicator,
            the next price is above the upper band of the bollinger band indicator and there is a filled current buy order (status ==1) 
            place a limit sell for desired asset quantity at the upper bollinger band value
            """
            #current_time_utc = dt.datetime.utcfromtimestamp(current_time/1000) #Binance timestamp is in ms, must / by 1000 to get seconds
            print('Current Price: ', next_price, '\nCreated Sell Order: ', self.bb['upper_band'][-1], '\nQuantity: ', self.buy_quantity, '\nTime: ', current_time)
            self.orders['time'].append(current_time)
            self.orders['order_limit'].append(self.bb['upper_band'][-1])
            self.orders['order_type'].append('sell')
            self.print_values()

    def plot_orders(self):
        """
        Plot all closing prices and indicators
        :return: Nothing
        """
        fig, axis = plt.subplots(2)

        #Only showing last s values for all values
        s = -1*self.show_times

        #Plot all checked prices and times, this leaves out the current incomplete closing price
        axis[0].plot_date(plt_dates.date2num(self.checked_times[s:]), self.checked_prices[s:], xdate=True, fmt='c-')

        #Plot bollinger bands
        axis[0].plot_date(plt_dates.date2num(self.bb['time'][s:]), self.bb['sma'][s:], xdate=True, fmt='k-') #-1 since sma not calculate for recent incomplete closing price
        axis[0].plot_date(plt_dates.date2num(self.bb['time'][s:]), self.bb['upper_band'][s:], xdate=True, fmt='k--')
        axis[0].plot_date(plt_dates.date2num(self.bb['time'][s:]), self.bb['lower_band'][s:], xdate=True, fmt='k--')

        #Plot stoch_rsi (%K_Slow, %D_Slow) in different subplot from time when buy_sell algorithm starts
        axis[1].plot_date(plt_dates.date2num(self.k_slow_array['time'][s:]), self.k_slow_array['k_slow'][s:], xdate=True, fmt='g-')
        axis[1].plot_date(plt_dates.date2num(self.d_slow_array['time'][s:]), self.d_slow_array['d_slow'][s:], xdate=True, fmt='b-')

        #Plot stoch_rsi user set upper and lower limits
        upper_limit = np.ones(shape=np.asarray(self.k_slow_array['time'][s:]).shape) * self.stoch_upper
        lower_limit = np.ones(shape=np.asarray(self.k_slow_array['time'][s:]).shape) * self.stoch_lower
        axis[1].plot_date(plt_dates.date2num(self.k_slow_array['time'][s:]), upper_limit, xdate=True, fmt='r--')
        axis[1].plot_date(plt_dates.date2num(self.k_slow_array['time'][s:]), lower_limit, xdate=True, fmt='r--')

        #Plot buy and sell orders
        orders = np.asarray(self.orders)
        buy_times = np.where( (np.asarray(self.orders['time']) > self.d_slow_array['time'][s]) & (np.asarray(self.orders['order_type']) == 'buy') )
        sell_times = np.where( (np.asarray(self.orders['time']) > self.d_slow_array['time'][s]) & (np.asarray(self.orders['order_type']) == 'sell') )
        if len(buy_times[0] > 0):
            axis[0].plot_date(plt_dates.date2num(np.take(self.orders['time'], buy_times[0])), np.take(self.orders['order_limit'], buy_times[0]), xdate=True, fmt='go')
        if len(sell_times[0] > 0):
            axis[0].plot_date(plt_dates.date2num(np.take(self.orders['time'], sell_times[0])), np.take(self.orders['order_limit'], sell_times[0]), xdate=True, fmt='ro')

        #Plot attributes
        axis[0].legend(labels=('Closing Prices', 'SMA', 'Bolling Upper Band', 'Bollinger Lower Band', 'Buy Orders', 'Sell Order'), loc='upper right', prop={'size':5})
        axis[1].legend(labels=('%k slow', '%d slow', 'user limits'), loc='upper right', prop={'size': 5})

        axis[0].set_xlabel('Date')
        axis[0].set_ylabel('USD')

        axis[1].set_xlabel('Date')
        axis[1].set_ylabel('%')

        fig.autofmt_xdate() #Auto aligns dates on x axis
        plt.show()

from deal.deal import *
from order_queue.order import Order
from order_queue.pair_queue import PairQueue
import ctypes
from log.logger import Logger
import redis
# create table trade_log (id int unsigned not null primary key AUTO_INCREMENT, stock_id varchar(20), buy_id varchar(20), sell_id varchar(20), price integer, volume integer time timestamp not null default current_timestamp)

class DealEngine:
    def __init__(self, stock_id, db_conn = None, redis_conn = None):
        self.stock_id = stock_id
        self.pair_queue = PairQueue(stock_id)
        self.logger = Logger('engine')
        self.db_conn = db_conn
        self.limit = 2
        if redis_conn is None:
            self.r = redis.Redis()
        else:
            self.r = redis_conn
        self.last_price = 4


    def on_trading(self):
        return True

    def save_deal(self, result,buy_order,sell_order):
        cursor = self.db_conn.cursor()
        result.price = 2
        result.buy_id = 1
        result.sell_id = 1
        print(result.buy_id)
        cursor.execute('insert into trade_log (stock_id,buy_id,sell_id,price,volume) values (%s,%s,%s,%s,%s) ',[result.stock_id,result.buy_id,result.sell_id,int(result.price),result.volume])
        cursor.execute('select enabled_money from fund_account_user where username=%s', [result.buy_id])
        buy_money = float(cursor.fetchall()[0][0])
        cursor.execute('select enabled_money from fund_account_user where username=%s', [result.sell_id])
        sell_money = float(cursor.fetchall()[0][0])
        buy_money -= result.volume * result.price
        sell_money += result.volume * result.price
        if buy_money < 0:
            return

        cursor.execute('select freezing_amount from security_in_account where username=%s', [result.sell_id])
        sell_freezing_security = int(cursor.fetchall()[0][0])
        sell_freezing_security -= result.volume

        #---------------------------------------------------------------------------------------------------------------
        # change security
        cursor.execute('select amount from security_in_account where username=%s', [result.sell_id])
        sell_security = int(cursor.fetchall()[0][0])
        sell_security -= result.volume
        cursor.execute('update security_in_account set amount = %s， freezing_amount = %s where username = %s',[sell_security,sell_freezing_security,result.sell_id])

        cursor.execute('select amount from security_in_account where username=%s', [result.buy_id])
        buy_security = int(cursor.fetchall()[0][0])
        buy_security += result.volume
        cursor.execute('update security_in_account set amount = %s where username = %s',
                       [buy_security, result.buy_id])

        #---------------------------------------------------------------------------------------------------------------
        cursor.execute('select freezing_money from fund_account_user where username=%s', [result.buy_id])
        buy_freezing_money = float(cursor.fetchall()[0][0])
        buy_freezing_money -= buy_order.get_price() * result.volume

        cursor.execute('select freezing_money from fund_account_user where username=%s', [result.sell_id])
        sell_freezing_money = float(cursor.fetchall()[0][0])
        sell_freezing_money -= sell_order.get_price() * result.volume
        cursor.execute('update fund_account_user set enabled_money=%s, freezing_money = %s where username=%s',[buy_money,buy_freezing_money,result.buy_id])
        cursor.execute('update fund_account_user set enabled_money=%s, freezing_money = %s where username=%s',[sell_money,sell_freezing_security,result.sell_id])
        # cursor.execute('update fund_account_user set enabled_money=%s where username=%s',[sell_money,result.sell_id])
        self.db_conn.commit()
        cursor.close()
        self.r.hset(result.stock_id,'last_price',result.price)
        print("deal finished")

    def deal(self):
        long_order, short_order = self.pair_queue.pop()
        if not long_order:
            self.logger.info("No Order Now")
            return False

        if not short_order:
            self.logger.info("No Order Now")
            return False
        a = ctypes.c_float(1.0)
        b = ctypes.c_double(1.0)
        dll = ctypes.CDLL('./deal/libdeal.so')
        dll.Deal.restype = exchange
        dll.Deal.argtypes = [
            stock,stock, ctypes.c_double, ctypes.c_double
        ]
        try:
            converted_long_order = order_conversion(long_order)
            converted_short_order = order_conversion(short_order)

            result = dll.Deal(converted_long_order,converted_short_order,a,b)
            print("finish")
            self.save_deal(result,long_order,short_order)
            re_order = regenerate_order(result=result)
            self.pair_queue.push(re_order)
            self.logger.info("Success")
        except ctypes.ArgumentError:
            print("in except")
            self.pair_queue.push(long_order)
            self.pair_queue.push(short_order)

        # converted_long_order = order_conversion(long_order)
        # converted_short_order = order_conversion(short_order)
        #
        # # dll = ctypes.CDLL('./deal/libdeal.so')
        #
        # a = ctypes.c_double(self.limit)
        # b = ctypes.c_double(self.last_price)
        # # dll.Deal.restype = exchange
        # result = dll.Deal(converted_long_order, converted_short_order,a,b)
        # self.save_deal(result,long_order,short_order)
        # re_order = regenerate_order(result=result)
        # # self.pair_queue.push(re_order)
        self.logger.info("Success")
        return True

    def run(self):
        while self.on_trading():
            self.deal()
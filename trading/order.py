from order_queue.pair_queue import PairQueue
from order_queue.queue import Queue
from order_queue.order import Order
from order_queue.constant import *
from flask import g
from flask import app
import redis
import mysql.connector
from db_config import *


class QueueManager():
    def __init__(self):
        self.queues = {}
        self.count = 0
        self.r = redis.Redis()
        self.db_conn = mysql.connector.connect(user=db_user, password=db_secret, database='EB', use_unicode=True)
        self.set_default_queues()

    def set_default_queues(self):
        cursor = self.db_conn.cursor()
        cursor.execute('select * from stock_set')
        result = cursor.fetchall()
        for item in result:
            stock_id = item[0]
            print(stock_id)
            stock_name = item[1]
            self.queues[stock_id] = PairQueue(stock_id, stock_name, self.r)
            mapping = {
                'stock_id': stock_id,
                'status': True,
                'last_price': 0,
            }
            self.r.hmset(item[0], mapping)

    def clean(self):
        self.r.flushall()
    def get_stock_id(self, stock_name):
        return self.r.hget(stock_name,'stock_id').decode('utf-8')
    def get_stock_status(self,stock_id):
        return self.r.hget(stock_id,'status').decode('utf-8')

    def set_stock_off(self,stock_id):
        self.r.hset(stock_id,'status',False)

    def set_stock_on(self,stock_id):
        self.r.hset(stock_id,'status',True)


    def add_queue(self):
        pass


    def check_queue(self):
        return True

    def get_pair_queue(self, stock_id):
        self.count += 1
        print("count "+ str(self.count))
        return self.queues[stock_id]


def get_queue_manager():
    queue_manager = getattr(g,'_queues',None)
    if queue_manager is None:
        queue_manager = g._queues = QueueManager()
    return queue_manager

# @app.appcontext_tearing_down
def teardown_queue_manager():
    pass

def stop_trading(stock_name):
    queue_manager = get_queue_manager()
    stock_id = queue_manager.get_stock_id(stock_name)
    queue_manager.set_stock_off(stock_name)

def start_trading(stock_name):
    queue_manager = get_queue_manager()
    stock_id = queue_manager.get_stock_id(stock_name)
    queue_manager.set_stock_on(stock_name)

def create_order( user_id, stock_id, direction, price, volume,db):
    queue_manager = get_queue_manager()
    if not check_user(user_id,stock_id,float(price),int(volume),int(direction),db):
        return -1
    # stock_id = queue_manager.get_stock_id(stock_name)
    order = Order(stock_id, user_id, price, volume, direction)
    pair_queue = queue_manager.get_pair_queue(stock_id)
    order_id = pair_queue.push(order)
    return order_id

def clean_queue(stock_name):
    queue_manager = get_queue_manager()
    stock_id = queue_manager.get_stock_id(stock_name)
    pair_queue = queue_manager.get_pair_queue(stock_id)
    pair_queue.clean()

def check_user(username,stock_name,price,volume,direction,db):
    print(trade_fund(username,volume * price, direction,db))
    print(trade_security(username,stock_name,volume,direction,db))
    check = False
    if direction is SHORT:
        check = trade_security(username,stock_name,volume,direction,db)
    else:
        check = trade_fund(username,volume * price, direction,db)
    return check
    # if trade_fund(username,volume * price, direction,db) and \
    #         trade_security(username,stock_name,volume,direction,db):
    #     return True

def get_user_orders(user_id):
    queue_manager = get_queue_manager()
    cursor = queue_manager.db_conn.cursor()
    # cursor = self.db_conn.cursor()
    cursor.execute('select * from stock_set')
    result = cursor.fetchall()
    order_list = []
    queue_manager = get_queue_manager()
    for item in result:
        stock_id = item[0]
        stock_name = item[1]
        # stock_list.appe
        pair_queue = queue_manager.get_pair_queue(stock_id)
        order_list.extend(pair_queue.user_orders(user_id))
    return order_list

def get_stock_orders(stock_id,type):
    queue_manager = get_queue_manager()
    # stock_id = queue_manager.get_stock_id(stock_name)
    pair_queue = queue_manager.get_pair_queue(stock_id)
    if type == SHORT:
        return pair_queue.get_short_orders()
    else:
        return pair_queue.get_long_orders()


def trade_fund(username, money, operation_type,db):
    # db =
    result = db.session.execute("select * from fund_account_user where username ='" + username + "'")
    if result.first() is None:
        return False
    result = db.session.execute(
        "select enabled_money,freezing_money from fund_account_user where username ='" + username + "'")
    fund = 0
    freeze_fund = 0
    new_fund = 0
    new_freeze_fund = 0
    for query_result in result:
        fund = float(str(query_result[0]))
        freeze_fund = float(str(query_result[1]))
    if operation_type == "buy":
        new_fund = fund
        new_freeze_fund = freeze_fund + money
    elif operation_type == "sell":
        new_fund = fund + money
        new_freeze_fund = freeze_fund
    if new_fund >= new_freeze_fund:
        new_fund = str(new_fund)
        new_freeze_fund = str(new_freeze_fund)
        result = db.session.execute("update fund_account_user set enabled_money=" + new_fund
                                    + ",freezing_money=" + new_freeze_fund + " where username ='" + username + "'")
        return True
    else:
        return False

def trade_security(username, security_number,amount,operation_type,db):
    result = db.session.execute("select * from security_in_account where username ='"
                                + username + "' and security_number='" + security_number + "'")
    if result.first() is None:
        return False
    result = db.session.execute("select amount,freezing_amount from security_in_account where username ='"
                                + username + "' and security_number='" + security_number + "'")
    security = 0
    freeze_security = 0
    new_security = 0
    new_freeze_security = 0
    for query_result in result:
        security = query_result[0]
        freeze_security = query_result[1]
    if operation_type == "sell":
        new_security = security
        new_freeze_security = freeze_security + amount
    elif operation_type == "buy":
        new_security = security + amount
        new_freeze_security = freeze_security
    if new_security >= new_freeze_security:
        new_security = str(new_security)
        new_freeze_security = str(new_freeze_security)
        result = db.session.execute("update security_in_account set amount=" + new_security
                                    + ",freezing_amount=" + new_freeze_security + " where username ='" + username
                                    + "' and security_number='" + security_number + "'")
        return True
    else:
        return False
def change_stock_status(stock_id, status):
    if status is True:
        start_trading(stock_id)
    else:
        stop_trading(stock_id)

def get_buy_sell_items(stock_id, is_buy):
    if is_buy:
        direction = LONG
    else:
        direction = SHORT
    return get_stock_orders(stock_id,direction)


def get_stock_state(stock_id):
    get = dict()
    get['stock_id'] = stock_id
    queue_manager = get_queue_manager()
    status = queue_manager.get_stock_status(stock_id)
    get['status'] = status
    pair_queue = queue_manager.get_pair_queue(stock_id)
    get['gains'] = pair_queue.get_gains()
    get['decline'] = pair_queue.get_decline()

def set_price_limit(stock_id, price, is_gains): # is_gains true设置涨幅 ，false 设置跌幅
    queue_manager = get_queue_manager()
    pair_queue = queue_manager.get_pair_queue(stock_id)
    if is_gains:
        pair_queue.set_gains(price)
    else:
        pair.queue.set_decline(price)
    return True
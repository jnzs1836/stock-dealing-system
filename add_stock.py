import pymysql
import datetime
import random

def add_stocks(stocks):
    # 打开数据库连接
    dbForOwner = pymysql.connect(user="owner",
                                 password="123456",
                                 db="EB",
                                 host="localhost",
                                 charset='utf8mb4')

    flag = 0
    sql = "insert into stock_set values(%s, %s)"
    args_list = []
    for i in stocks:
        args = []
        args.append(i)
        args.append(stocks[i])
        args_list.append(args)

    cur = dbForOwner.cursor()

    try:
        for i in args_list:
            cur.execute(sql, i)
        dbForOwner.commit()
        flag = 1

    except Exception as e:
        flag = 0

    finally:
        dbForOwner.close()
        return flag

def add_stocks_previous_price(stocks, py, pm, pd):
    # 打开数据库连接
    dbForOwner = pymysql.connect(user="owner",
                                 password="123456",
                                 db="EB",
                                 host="localhost",
                                 charset='utf8mb4')

    today = datetime.datetime.now()

    p_day = datetime.datetime(py, pm, pd)

    flag = 0
    sql = "insert into previous_stock values(%s, %s, %s, %s, %s, %s, %s)"

    cur = dbForOwner.cursor()

    try:
        args_list = []
        n = len(stocks)
        j = 0
        for i in stocks:
            args = []
            args.append(i)
            args.append(stocks[i])
            max = random.uniform(5.0, 200)
            min = max * (1 - random.uniform(0, 0.2 / 1.1))
            start = random.uniform(min, max)
            end = random.uniform(min, max)
            args.append(start)
            args.append(end)
            args.append(max)
            args.append(min)
            args.append(p_day.strftime("%Y-%m-%d"))
            args_list.append(args)

        p_day = p_day + datetime.timedelta(days=+1)
        while p_day < today:
            t = 0
            for i in stocks:
                args = []
                args.append(i)
                args.append(stocks[i])
                max = args_list[j+t][3] * (1 + random.uniform(0, 0.2) - 0.1)
                if max < 5.0:
                    max = args_list[j+t][3] * (1 + random.uniform(0, 0.1))
                min = max * (1 - random.uniform(0, 0.2/1.1))
                start = random.uniform(min, max)
                end = random.uniform(min, max)
                args.append(start)
                args.append(end)
                args.append(max)
                args.append(min)
                args.append(p_day.strftime("%Y-%m-%d"))
                args_list.append(args)
                t = t + 1

            p_day = p_day + datetime.timedelta(days=+1)
            j = j + n

        for i in args_list:
            cur.execute(sql, i)
        dbForOwner.commit()
        flag = 1

    except Exception as e:
        flag = 0
        raise e

    finally:
        dbForOwner.close()
        return flag


def add_notice(stocks):
    # 打开数据库连接
    dbForOwner = pymysql.connect(user="owner",
                                 password="123456",
                                 db="EB",
                                 host="localhost",
                                 charset='utf8mb4')

    flag = 0
    sql = "insert into notice values(%s, %s)"
    args_list = []
    for i in stocks:
        args = []
        args.append(i)
        args.append(str(i) + "'s notice")
        args_list.append(args)

    cur = dbForOwner.cursor()

    try:
        for i in args_list:
            cur.execute(sql, i)
        dbForOwner.commit()
        flag = 1

    except Exception as e:
        flag = 0

    finally:
        dbForOwner.close()
        return flag


if __name__ == "__main__":
    stocks = {}  # id: name
    for i in range(40):
        stocks[i+100] = "s" + str(i)
    # add_stocks(stocks)
    # add_notice(stocks)
    py = 2010
    pm = 1
    pd = 1
    add_stocks_previous_price(stocks, py, pm, pd)

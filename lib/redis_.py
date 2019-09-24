import threading
import time

import redis

from config import REDIS_HOST, REDIS_PASSWORD, NODE_NAME
from lib.common import lstrsub

redis_lock = threading.Lock()


def redis_connect():
    host, port = REDIS_HOST.split(":")
    print(host)
    print(port)
    print(REDIS_PASSWORD)

    r = redis.Redis(host='127.0.0.1', port=6379, password=None)

    while True:
        print("redis check...")
        try:
            r.ping()
            break
        except:
            pass
        time.sleep(3)
    print("redis check success..")
    pool = redis.ConnectionPool(host=host, port=port,
                                decode_responses=True, password=REDIS_PASSWORD
                                # host是redis主机，需要redis服务端和客户端都起着 redis默认端口是6379
                                )
    redis_con = redis.Redis(connection_pool=pool)
    return redis_con


def add_redis_log(log):
    """
    添加任务log到redis队列，并对redis队列进行清理，如果超过500则弹出老的
    :param log:
    :return:
    """
    # 节点信息？
    node_name = "w12_log_{}".format(lstrsub(NODE_NAME, "w12_node_"))
    redis_lock.acquire()
    redis_con.lpush(node_name, repr(log))  # 执行 LPUSH 命令后，列表的长度。
    while redis_con.llen(node_name) > 500:
        redis_con.rpop(node_name)
    redis_lock.release()


def task_update(key: str, value: int):
    """

    :param key:tasks running finished
    :param value:
    :return:
    """
    redis_lock.acquire()
    field = ["tasks", "running", "finished"]
    if key not in field:
        print("{key} error ".format(key=key))
        return False
    if key == "running" or key == "finished":
        redis_con.hincrby(NODE_NAME, key, value)
        """
        自增自减整数(将key对应的value--整数 自增1或者2，或者别的整数 负数就是自减)hincrby(name, key, amount=1)
        自增name对应的hash中的指定key的值，不存在则创建key=amount参数：name，redis中的name key， hash对应的key amount，自增数（整数）
        """
    else:
        redis_con.hset(NODE_NAME, key, value)
        """
        hset(name, key, value)
        name对应的hash中设置一个键值对（不存在，则创建；否则，修改）
        参数：
        name，redis的name
        key，name对应的hash中的key
        value，name对应的hash中的value
        """
    redis_lock.release()


redis_con = redis_connect()
if __name__ == '__main__':
     redis_con = redis_connect()
    # r = redis.Redis(host='127.0.0.1', port=6379, password=None)

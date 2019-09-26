# 创建linux端python程序控制程序
import os
import threading

import time

from config import THREAD_NUM, DEBUG, NODE_NAME
from lib.data import PATHS, logger
from lib.engine import Schedular
from lib.redis_ import redis_con
from thirdpart.requests import patch_all

schedular = Schedular(threadnum=THREAD_NUM)


def moudle_path():
    """
        This will get us the program's directory
    """
    return os.path.dirname(os.path.realpath(__file__))


def redis_get():
    list_name = "w12scan_scanned"
    while 1:
        target = redis_con.blpop(list_name)[1]
        print(target)
        schedular.put_target("https://blog.csdn.net")
        schedular.put_target(target)


def debug_get():
    target = "http://stun.tuniu.com"
    schedular.put_target(target)


def node_register():
    first_blood = True
    while 1:
        print("node_register")
        if first_blood:
            dd = {
                "last_time": time.time(),
                "tasks": 0,
                "running": 0,
                "finished": 0
            }
            redis_con.hmset(NODE_NAME, dd)
            first_blood = False
        else:
            redis_con.hset(NODE_NAME, "last_time", time.time())
        time.sleep(50 * 5)


def main():
    PATHS.ROOT_PATH = moudle_path()
    print(PATHS.ROOT_PATH)
    PATHS.PLUGIN_PATH = os.path.join(PATHS.ROOT_PATH, "pocs")
    print(PATHS.PLUGIN_PATH)
    PATHS.OUTPUT_PATH = os.path.join(PATHS.ROOT_PATH, "output")
    print(PATHS.OUTPUT_PATH)
    PATHS.DATA_PATH = os.path.join(PATHS.ROOT_PATH, "data")
    print(PATHS.DATA_PATH)

    patch_all()

    logger.info("Hello W12SCAN !")

    # domain域名整理（统一格式：无论是域名还是二级目录，右边没有 /），ip cidr模式识别，ip整理
    # 访问redis获取目标

    schedular.start()
    # 启动任务分发调度器
    if DEBUG:
        func_target = debug_get
    else:
        func_target = redis_get

    # 与WEB的通信线程
    node = threading.Thread(target=node_register)
    node.start()

    # 队列下发线程
    t = threading.Thread(target=func_target, name='LoopThread')
    t.start()
    try:
        schedular.run()
    except KeyboardInterrupt:
        logger.info("User exit")


if __name__ == '__main__':
    main()

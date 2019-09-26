# 分发调度引擎
import os
import random
import socket
import threading
from concurrent import futures
from concurrent.futures import thread
from queue import Queue

import time

import _thread
from urllib.parse import urlparse

import requests
import sys

from config import NUM_CACHE_IP, MASSCAN_DEFAULT_PORT, MASSCAN_FULL_SCAN, IS_START_PLUGINS, THREAD_NUM, NUM_CACHE_DOMAIN

from lib.common import is_ip_address_format, is_url_format
from lib.data import PATHS, collector, logger
from lib.loader import load_remote_poc, load_string_to_moudle
from lib.redis_ import task_update

from plugins import crossdomain

from plugins import gitleak
from plugins import iis_parse
from plugins import ip_location

from plugins import phpinfo
from plugins import svnleak
from plugins import tomcat_leak
from plugins import wappalyzer
from plugins import webeye
from plugins import webtitle
from plugins import whatcms
from plugins.masscan import masscan
from plugins.nmap import nmapscan
from thirdpart.requests import patch_all


class Schedular:
    def __init__(self, threadnum=1):
        self.queue = Queue()
        self.ip_queue = Queue()
        self.threadNum = threadnum
        self.lock = threading.Lock()
        self.cache_ips = []  # IP缓冲池
        self.cache_domains = []  # 域名缓冲池
        # change
        # logger.info()

    def put_target(self, target):
        # 判断是IP还是域名，加入不同的字段
        if is_ip_address_format(target):
            serviceType = "ip"
        elif is_url_format(target):
            serviceType = "domain"
            target = target.rstrip('/')
        else:
            serviceType = "other"

        tmp = {
            "target": target,
            "serviceType": serviceType
        }
        if serviceType == "ip":
            self.ip_queue.put(tmp)
        else:
            self.queue.put(tmp)
        task_update("tasks", self.queue.qsize() + self.ip_queue.qsize())
        # 通知redis组件对redis信息进行更新
        # 到底是怎么更新的啊

    def receive_ip(self):

        while 1:
            struct = self.ip_queue.get()
            serviceType = struct.get("serviceType", "other")
            task_update("tasks", self.queue.qsize() + self.ip_queue.qsize())
            if serviceType == "ip":
                flag = False
                self.lock.acquire()
                self.cache_ips.append(struct)
                num = len(self.cache_ips)
                if num >= NUM_CACHE_IP:
                    flag = True
                    serviceTypes = self.cache_ips  # 获取缓冲？
                    self.cache_ips = []
                self.lock.release()
                if not flag:
                    self.ip_queue.task_done()
                    continue
                task_update("running", 1)
                try:
                    self.hand_ip(serviceTypes)
                except Exception as e:
                    continue
                logger.error("hand ip error:{}".format(repr(e)))
                logger.error(repr(sys.exc_info()))
                task_update("running", -1)
            self.ip_queue.task_done()
            task_update("tasks", self.queue.qsize() + self.ip_queue.qsize())

    def receive(self):

        while 1:

            try:
                struct = self.queue.get(timeout=1)
            except Exception as e:
                continue

            task_update("tasks", self.queue.qsize() + self.ip_queue.qsize())

            serviceType = struct.get("serviceType", "other")
            if serviceType == "other":
                msg = "not matches targets:{}".format(repr(struct))
                logger.error(msg)
                self.queue.task_done()
                continue

            elif serviceType == "domain":
                flag = False
                self.lock.acquire()
                self.cache_domains.append(struct)
                num = len(self.cache_domains)
                if num >= NUM_CACHE_DOMAIN:
                    flag = True
                    serviceTypes = self.cache_domains
                    # 刷新缓存列表
                    self.cache_domains = []
                self.lock.release()
                if not flag:
                    self.queue.task_done()
                    continue
                    # 多线程启动扫描域名
                for serviceType in serviceTypes:
                    task_update("running", 1)
                    try:
                        self.hand_domain(serviceType)
                    except Exception as e:
                        logger.error("hand domain error :{}".format(repr(e)))
                        logger.error(repr(sys.exc_info()))
                    task_update("running", -1)
            self.queue.task_done()
            task_update("tasks", self.queue.qsize() + self.ip_queue.qsize())


    def start(self):

        for i in range(self.threadNum - 1):
            print(i)
            _thread.start_new_thread(self.receive, ())
        _thread.start_new_thread(self.receive_ip, ())

    def nmap_result_handle(self, result_nmap: dict, host):
        # 处理nmap插件返回的数据
        if result_nmap is None:
            return None
        result2 = {}
        for port, portInfo in result_nmap.items():
            if host not in result2:
                result2[host] = []
            if portInfo["state"] != "open":
                continue
            name = portInfo.get("name", "")
            # hand nmap bug
            product = portInfo.get("product", "")
            version = portInfo.get("version", "")
            extrainfo = portInfo.get("extrainfo", "")

            if "http" in name and "https" not in name:
                if port == 443:
                    _url = "https://{0}:{1}".format(host, port)
                else:
                    _url = "http://{0}:{1}".format(host, port)
                self.put_target(_url)
            elif "https" in name:
                _url = "https://{0}:{1}".format(host, port)
                self.put_target(_url)
            result2[host].append(
                {"port": port, "name": name, "product": product, "version": version, "extrainfo": extrainfo})
            return result2

    def hand_ip(self, serviceTypes, option='masscan'):
        ip_list = []

        for item in serviceTypes:
            ip_list.append(item["target"])
        ports = MASSCAN_DEFAULT_PORT
        result2 = {}
        if option == 'masscan':
            if MASSCAN_FULL_SCAN:
                ports = "1-65535"
            target = os.path.join(PATHS.OUTPUT_PATH, "target_{0}.log".format(time.time()))
            with open(target, "w+") as fp:
                fp.write('\n'.join(ip_list))
            logger.debug("ip:" + repr(ip_list))
            try:
                result = masscan(target, ports)
            except Exception as e:
                logger.error("masscan error msg:{}".format(repr(e)))
                result = None
            if result is None:
                return None
            for host, ports in result.times():
                ports = list(ports)
                if host not in result2:
                    result2[host] = []
                task_update("running", 1)
                try:
                    result_nmap = nmapscan(host, ports)
                except:
                    result_nmap = None
                task_update("runnning", -1)
                if result_nmap is None:
                    for tmp_port in ports:
                        result2[host].append({"port": tmp_port})
                    continue
                tmp_r = self.nmap_result_handle(result_nmap, host=host)
                result2.update(tmp_r)
        elif option == "nmap":
            logger.debug("ip:" + repr(ip_list))
            for host in ip_list:
                result_nmap = nmapscan(host, ports.split(","))
                tmp_r = self.nmap_result_handle(result_nmap, host=host)
                if tmp_r:
                    result2.update(tmp_r)
        data = {}

        # 返回所有的ip，并且根据代码寻找对应的地理信息
        for ip in result2.keys():
            if ip not in data:
                data[ip] = {}
            d = ip_location.poc(ip)
            if d:
                data[ip]["location"] = d
            data[ip]["infos"] = result2[ip]

        collector.add_ips(data)
        # 将信息全部保存，然后发送信息，将信息发送至前端
        for ip in result2.keys():
            collector.send_ok_ip(ip)

    def hand_domain(self, serviceType):
        target = serviceType["target"]
        logger.info(target)
        # 添加这条记录
        collector.add_domain(target)
        # 发起请求
        try:
            r = requests.get(target, timeout=30, verify=False, allow_redirects=False)
            collector.add_domain_info(target,
                                      {"headers": r.headers, "body": r.text, "status_code": r.status_code})
        except Exception as e:
            logger.error("request url error:" + str(e))
            collector.del_domain(target)
            return
        logger.debug("target:{} over,start to scan".format(target))

        # Get hostname
        # ???????????WDNMD
        hostname = urlparse(target).netloc.split(":")[0]
        if not is_ip_address_format(hostname):
            try:
                # return the host from socket
                _ip = socket.gethostbyname(hostname)
                collector.add_domain_info(target, {"ip": _ip})
            except:
                pass
        else:
            collector.add_domain_info(target, {"ip": hostname})
        # 需要启动那些poc进行目标信息扫描
        work_list = [webeye.poc, webtitle.poc, wappalyzer.poc]
        # password_found.poc

        if IS_START_PLUGINS:
            pass
            work_list.append(crossdomain.poc)
            # work_list.append(directory_browse.poc)
            work_list.append(gitleak.poc)
            work_list.append(iis_parse.poc)
            work_list.append(phpinfo.poc)
            work_list.append(svnleak.poc)
            work_list.append(tomcat_leak.poc)
            # work_list.append(whatcms.poc)

        # 信息直接从函数的内部利用collector进行存储

        for func in work_list:
            try:
                func(target)
            except Exception as e:
                logger.error("domain plugin threading error {}:{}".format(repr(Exception), str(e)))
                pass
        logger.debug("target:{} End of scan".format(target))
        collector.print_domains()
        infos = collector.get_domain(target)
        _pocs = []
        temp = {}
        if IS_START_PLUGINS and "CMS" in infos:
            if infos.get("app"):
                temp["app"] = []
                temp["app"].append(infos["CMS"])
            else:
                temp["app"] = [infos["CMS"]]
            # update domain app
            collector.add_domain_info(target, temp)

        if temp.get("app"):
            keywords = temp["app"]
            # 远程读取插件
            pocs = load_remote_poc()

            for poc in pocs:
                for keyword in keywords:
                    webfile = poc["webfile"]
                    logger.debug("load {0} poc:{1} poc_time:{2}".format(poc["type"], webfile, poc["time"]))

                    # 加载插件 加载远程文件目录 将其转换成实体

                    code = requests.get(webfile).text
                    obj = load_string_to_moudle(code, webfile)
                    # 在模块对象列表中加入远程模块
                    _pocs.append(obj)
        # 并发执行插件
        if _pocs:
            executor = futures.ThreadPoolExecutor(len(_pocs))
            fs = []
            for f in _pocs:
                taks = executor.submit(f.poc, target)
                # 这儿返回的是啥子鸡巴啊  每个线程的控制类？
                fs.append(taks)
            for f in futures.as_completed(fs):
                try:
                    res = f.result()
                except Exception as e:
                    res = None
                    logger.error("load poc error:{} error:{}".format(target, str(e)))
                if res:
                    name = res.get("name") or "scan_" + str(time.time())
                    collector.add_domain_bug(target, {name: res})
        # 通过异步调用插件得到返回结果，并且通过collector返送结果
        collector.send_ok(target)
        print("print collector")
        print(collector.collect_domains)

    def run(self):
        while 1:
            # 对剩余未处理的域名进行处理
            if self.cache_domains:
                self.lock.acquire()
                service_types = self.cache_domains
                self.cache_domains = []
                self.lock.release()

                for serviceType in service_types:
                    task_update("running", 1)
                    try:
                        self.hand_domain(serviceType)
                    except Exception as e:
                        logger.error(repr(sys.exc_info()))
                        pass
                    task_update("running", -1)

            # 对剩余未处理的ip进行处理
            if self.cache_ips:
                self.lock.acquire()
                service_types = self.cache_ips
                self.cache_ips = []
                self.lock.release()

                task_update("running", 1)

                try:
                    self.hand_ip(service_types)
                except Exception as e:
                    logger.error(repr(sys.exc_info()))
                    pass
                task_update("runnning", -1)

            # 最后一次提交
            collector.submit()
            task_update("tasks", self.queue.qsize() + self.ip_queue.qsize())
            time.sleep(random.randint(2, 10))

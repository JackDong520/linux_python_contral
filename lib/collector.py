import queue
import threading

from urllib.parse import urljoin

import copy
import requests


class Collector:
    def __init__(self):
        self.collect_lock = threading.Lock()
        self.collect_domains = {}
        self.collect_ips = {}
        # domain cache 缓存队列
        self.cache_queue = queue.Queue()
        # ip cache 缓存队列
        self.cache_ips = queue.Queue()

    def add_domain(self, domain):
        self.collect_lock.acquire()
        if domain not in self.collect_domains:  # 如果该域名之前没有创建，创建一个新的集合装数据
            self.collect_domains[domain] = {}
        self.collect_lock.release()

    def add_domain_info(self, domain, infos: dict):
        if domain not in self.collect_domains:
            self.add_domain(domain)
        for k, v in infos.items():
            self.collect_lock.acquire()
            self.collect_domains[domain][k] = v
            self.collect_lock.release()

    def add_domain_bug(self, domain, infos: dict):
        self.collect_lock.acquire()
        if "bugs" not in self.collect_domains[domain]:
            self.collect_domains[domain]["bugs"] = {}
        for k, v in infos.items():
            self.collect_domains[domain]["bugs"][k] = v
        self.collect_lock.release()

    def add_ips(self, infos: dict):
        for k, v in infos.items():
            self.collect_lock.acquire()
            self.collect_ips[k] = v
            self.collect_lock.release()

    def get_ip(self, target):
        self.collect_lock.acquire()
        data = copy.deepcopy(self.collect_ips[target])
        self.collect_lock.release()
        return data

    def get_domain(self, domain):
        self.collect_lock.acquire()
        if domain in self.collect_domains:
            data = copy.deepcopy(self.collect_domains[domain])
        else:
            data = {}
        self.collect_lock.release()
        # 删除一些不想显示的key
        if data.get("headers"):
            tmp_headers = "\n".join(k + ":" + v for k, v in data["headers"].items())
            del data["headers"]
            data["headers"] = tmp_headers
        return data

    def get_domain_info(self, domain, k):
        self.collect_lock.acquire()
        ret = self.collect_domains[domain].get(k, None)
        self.collect_lock.release()
        return ret

    def del_domain(self, domain):
        self.collect_lock.acquire()
        del self.collect_domains[domain]
        self.collect_lock.release()

    def del_ip(self, target):
        self.collect_lock.acquire()
        del self.collect_ips[target]
        self.collect_lock.release

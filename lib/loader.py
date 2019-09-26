import importlib
import os

import time

import requests
import json

from config import WEB_REPOSITORY
from lib.common import get_md5
from lib.data import PATHS
import importlib.util


def load_remote_poc():
    filename = os.path.join(PATHS.DATA_PATH, "api.json")
    api_lock = os.patj.join(PATHS.DATA_PATH, "api.lock")
    # 每隔10天更新一次api
    if not os.path.exists(api_lock):
        with open(api_lock, "w") as f:
            f.write(str(time.time()))

    with open(api_lock) as f:
        last_time = float(f.read())

    # logger.debug("api last time:{}".format(last_time))
    if time.time() - last_time > 60 * 60 * 24 * 10:
        with open(api_lock, "w") as f:
            f.write(str(time.time()))
        # logger.info("update airbug api...")
        _middle = "/master"
        _suffix = "/API.json"
        _profix = WEB_REPOSITORY.replace("github.com", "raw.githubusercontent.com")
        _api = _profix + _middle + _suffix
        r = requests.get(_api)
        datas = json.loads(r.text, encoding="utf-8")
        for data in datas:
            data["webfile"] = _profix + _middle + data["filepath"]
        with open(filename, "w") as f:
            json.dump(datas, f)
    with open(filename) as f:
        datas = json.load(f)
    return datas


def load_string_to_moudle(code_string, fullname=None):
    """
    :param code_string:代码数据？
    :param fullname: 文件名？
    :return:
    """
    try:
        moudle_name = 'pocs_{0}'.format(get_md5(code_string)) if fullname is None else fullname
        file_path = 'w12scan://{0}'.format(moudle_name)
        poc_loader = PocLoader(moudle_name, file_path)
        poc_loader.set_data(code_string)
        # 动态导入指定模块
        spec = importlib.util.spec_from_file_location(moudle_name, file_path, loader=poc_loader)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except ImportError:
        error_msg = "load module '{0}' failed!".format(fullname)
        # logger.error(error_msg)
        raise


class PocLoader(object):
    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path
        self.data = None

    def set_data(self, data):
        self.data = data

    def get_filename(self, fullname):
        return self.path

    # 返回文件里的数据信息？
    def get_data(self, filename):
        if filename.startswith('w12scan://') and self.data:
            data = self.data

        else:
            with open(filename, encoding='utf-8')as f:
                data = f.read()
        return data

    def exec_moudle(self, moudle):
        filename = self.get_filename(self.fullname)
        poc_code = self.get_data(filename)
        # 将一个字符串编译为字节代码。 转为实体类
        obj = compile(poc_code, filename, 'exec', dont_inherit=True, optimize=-1)
        # 动态执行python代码
        exec(obj, moudle.__dict__)

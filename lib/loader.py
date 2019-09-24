import os

import time

import requests
import json

from config import WEB_REPOSITORY
from lib.data import PATHS


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

import _thread
import redis
import requests


def test():
    print("wdnmd")


if __name__ == '__main__':
    for i in range(10):
        _thread.start_new_thread(test, ())

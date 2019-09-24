import redis

if __name__ == '__main__':
    #   s = ['1', '2']
    # sta = "12345"
    # if s not in sta:
    #    print(sta)

    # filters = ['招聘', '诚聘', '社招']
    # contents = [
    #     '独自等待安全团队诚聘, //www.jb51.net/',
    #     '独自等待安全团队招聘, //www.jb51.net/',
    #     '独自等待安全团队社招, //www.jb51.net/',
    #     '独自等待信息安全博客, //www.jb51.net/',
    # ]
    #
    # for content in contents:
    #     print(content)

    # b = 'hello world'
    # tmp_b = '\n'.join(b)
    # print(tmp_b)

    # dict = {'runoob': 'runoob.com', 'google': 'google.com'}
    # print(dict)
    # print(repr(dict))


    re = redis.Redis(host='127.0.0.1', port=6379, password=None)
    re.set('key_name', 'value_tom')
    print(re.get('key_name'))

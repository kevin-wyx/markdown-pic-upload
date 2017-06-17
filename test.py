# -*- coding: utf-8 -*-
import sys

from vonder import qiniu


def test_qiniu_upload():
    file_path = sys.argv[1]
    service = qiniu.ServiceProvider()
    ret = service.upload(file_path)
    print ret
    return ret


if __name__ == '__main__':
    test_qiniu_upload()

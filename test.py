# -*- coding: utf-8 -*-
import sys

from vonder import qiniu
from markdown_parser import Parser


def test_qiniu_upload():
    file_path = sys.argv[1]
    sp = qiniu.ServiceProvider()
    ret = sp.upload(file_path)
    print ret
    return ret


def test_auto_parse():
    file_path = sys.argv[1]
    parser = Parser(file_path)
    parser.upload_image_and_replace()


if __name__ == '__main__':
    test_auto_parse()

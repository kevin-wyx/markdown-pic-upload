# -*- coding: utf-8 -*-
import random

url_unsafe_chars = [
    ('{', '%7B'), ('}', '%7D'), ('|', '%7C'), ('\\', '%5C'), ('^', '%5E'),
    ('~', '%7E'), ('[', '%5B'), (']', '%5D'), ('`', '%60'), (' ', '%20'),
    ('"', '%22'), ('<', '%3C'), ('>', '%3E'), ('#', '%23'), ('%', '%25'),
    (';', '%3B'), ('/', '%2F'), ('?', '%3F'), (':', '%3A'), ('@', '%40'),
    ('=', '%3D'), ('&', '%26')]


def get_random_str(chars, size=5):
    return ''.join([random.choice(chars) for i in xrange(size)])


def url_safe_str(s):
    for char, quoted in url_unsafe_chars:
        s = s.replace(char, quoted)
    return s

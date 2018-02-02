# -*- coding: utf-8 -*-
from ConfigParser import SafeConfigParser
import datetime
import heapq
import os
import re
import string
import uuid

import vonder
from tools import util

config_parser = SafeConfigParser()
config_parser.read('server.conf')
using_sp = config_parser.get('default', 'use')

UPLOAD_PREFIX = """<!---\nmd-pic-upload-prefix: %(prefix)s\nprefix-create-time: %(time)s\n-->\n\n\n"""  # noqa


class Parser(object):
    def __init__(self, file_path):
        self.file_path = file_path.rstrip('/')
        self.file_dir = os.path.dirname(file_path)
        self.images = []
        self.image_names = []
        self.read_size = 50000
        self.pattern1 =\
            re.compile(r"!\[.*\]\(([a-zA-Z0-9\-\_\.\/]+)(\s+(\"[^\"]*\")?)?\)")
        self.pattern2 = re.compile(r"<\s*img.*\s+src\s*=\s*([\'\"])(.+?)\1.*>")
        self.broken_img_tag_search_len = 300
        self.broken_img_tag_pattern =\
            re.compile(r"!\[?.*\]?\(?[a-zA-Z0-9\-\_\.\/]*( +(\"[^\"]*\")?)?[^\)\s]$")  # noqa
        self.finish_reading = False
        self.upload_prefix_pattern = \
            re.compile(r'<!---.+md-pic-upload-prefix:\s*(\w+).*-->', re.DOTALL)
        self.prefix = None
        self.prefix_in_file = False

    def read_passage(self, file_handler, last_position):
        passage = file_handler.read(self.read_size)
        if not passage:
            self.finish_reading = True
        suffix = passage[-1 * self.broken_img_tag_search_len:]
        suffix_len = len(suffix)
        suffix = suffix.rstrip()
        match_borken = self.broken_img_tag_pattern.search(suffix)
        current_position = file_handler.tell()
        if match_borken:
            broken_len = suffix_len - match_borken.start()
            passage = passage[:-1 * broken_len]
            current_position -= broken_len
            file_handler.seek(current_position)
        if last_position == current_position:
            self.finish_reading = True
        return passage, current_position

    def get_all_image_path(self):
        print "===>Getting all images"
        with open(self.file_path, 'r') as file_handler:
            position = 0
            while True:
                last_position = position
                passage, position = self.read_passage(file_handler, position)
                if self.finish_reading:
                    break
                if not passage:
                    continue

                if not self.prefix_in_file:
                    matched = self.upload_prefix_pattern.search(passage)
                    if matched:
                        self.prefix = matched.group(1)
                        self.prefix_in_file = True

                for match in self.pattern1.finditer(passage):
                    image_path = match.group(1)
                    start = match.start(1) + last_position
                    end = match.end(1) + last_position
                    heapq.heappush(self.images, (start, end, image_path))
                for match in self.pattern2.finditer(passage):
                    image_path = match.group(1)
                    start = match.start(1) + last_position
                    end = match.end(1) + last_position
                    heapq.heappush(self.images, (start, end, image_path))

    def is_url(self, path):
        return re.match(r'\w+\:\/\/[^\/].+', path)

    def get_absolute_path(self, path):
        if path.startswith('.'):
            return os.path.join(self.file_dir, path)
        else:
            return path

    def write_to_new_file(self, old_handler, new_handler,
                          start, end=None):
        size = end - start
        old_handler.seek(start)
        write_sth = False
        while True:
            if size > self.read_size:
                read_size = self.read_size
            elif 0 < size <= self.read_size:
                read_size = size
            else:
                break
            content = old_handler.read(read_size)
            if content:
                new_handler.write(content)
                new_handler.flush()
                write_sth = True
                size -= self.read_size
            else:
                break
        return write_sth

    def rename_image(self, image_abs_path):
        name = image_abs_path.rsplit('/')[-1]
        while True:
            if name in self.image_names:
                rand_str = util.get_random_str(
                    string.digits + string.letters)
                name = '%s-%s' % (rand_str, name)
            else:
                break
        self.image_names.append(name)
        return name

    def upload_image_and_replace(self):
        print "===>Parsing markdown file"
        self.get_all_image_path()
        if not self.prefix_in_file:
            self.prefix = str(uuid.uuid4()).replace('-', '')
        sp = getattr(vonder, using_sp).ServiceProvider(self.prefix)
        print "===>Started upload and replace images"
        now = datetime.datetime.now().strftime('%y%m%d%H%M%S')
        new_file_path = '%s.%s' % (self.file_path, now)
        with open(new_file_path, 'w') as new_file:
            with open(self.file_path, 'r') as file:
                if not self.prefix_in_file:
                    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    prefix_comment = UPLOAD_PREFIX % \
                        {'time': now, 'prefix': self.prefix}
                    new_file.write(prefix_comment)

                seek_start = 0
                while True:
                    try:
                        start, end, image_path = heapq.heappop(self.images)
                    except IndexError:
                        break

                    if self.is_url(image_path):
                        continue
                    abs_path = self.get_absolute_path(image_path)
                    print "   ===>Uploading", abs_path
                    new_name = util.url_safe_str(self.rename_image(abs_path))
                    ret_data = sp.upload(abs_path, rename=new_name)
                    image_url = ret_data['download_url']
                    if type(image_url) is unicode:
                        image_url = image_url.encode('utf-8')
                    print "   ===>Got", image_url
                    seek_end = start
                    self.write_to_new_file(
                        file, new_file, seek_start, seek_end)
                    new_file.write(image_url)
                    seek_start = end
                while True:
                    seek_end = seek_start + self.read_size
                    if not self.write_to_new_file(
                       file, new_file, seek_start, seek_end):
                        break
                    seek_start = seek_end

        print "===>All Done!"
        print "===>Saved as", new_file_path

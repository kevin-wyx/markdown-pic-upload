# -*- coding: utf-8 -*-
from configparser import SafeConfigParser
import datetime
import heapq
import os
import re
import string
import util

import vonder

config_parser = SafeConfigParser()
config_parser.read('server.conf')
using_sp = config_parser.get('default', 'use')


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
        prefix = self.get_upload_prefix()
        self.sp = getattr(vonder, using_sp).ServiceProvider(prefix)

    def get_all_image_path(self):
        print "===>Getting all images"
        with open(self.file_path, 'r') as file_handler:
            count = 0
            while True:
                passage = file_handler.read(self.read_size)
                for match in self.pattern1.finditer(passage):
                    image_path = match.group(1)
                    start = match.start(1) + self.read_size * count
                    end = match.end(1) + self.read_size * count
                    heapq.heappush(self.images, (start, end, image_path))
                for match in self.pattern2.finditer(passage):
                    image_path = match.group(1)
                    start = match.start(1) + self.read_size * count
                    end = match.end(1) + self.read_size * count
                    heapq.heappush(self.images, (start, end, image_path))
                if not passage:
                    break
                count += 1

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
            new_handler.write(old_handler.read(read_size))
            new_handler.flush()
            write_sth = True
            size -= self.read_size
        return write_sth

    def get_upload_prefix(self):
        print "file_path:", self.file_path
        if '/' in self.file_path:
            file_name = self.file_path.rsplit('/')[-1]
        else:
            file_name = self.file_path
        file_name = util.url_safe_str(file_name)
        print "file_name:", file_name
        now = datetime.datetime.now().strftime('%Y%m%d')
        rand_str = util.get_random_str(string.digits + string.letters)
        return '%s-%s-%s' % (now, rand_str, file_name)

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
        print "===>Started upload and replace images"
        now = datetime.datetime.now().strftime('%y%m%d%H%M%S')
        new_file_path = '%s.%s' % (self.file_path, now)
        with open(new_file_path, 'w') as new_file:
            with open(self.file_path, 'r') as file:
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
                    ret_data = self.sp.upload(abs_path, rename=new_name)
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

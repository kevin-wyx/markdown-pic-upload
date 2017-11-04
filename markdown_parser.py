# -*- coding: utf-8 -*-
from configparser import SafeConfigParser
import datetime
import heapq
import os
import re

import vonder

config_parser = SafeConfigParser()
config_parser.read('server.conf')
using_sp = config_parser.get('default', 'use')


class Parser(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_dir = os.path.dirname(file_path)
        self.images = []
        self.read_size = 50000
        self.pattern1 =\
            re.compile(r"!\[.*\]\(([a-zA-Z0-9\-\_\.\/]+)(\s+(\"[^\"]*\")?)?\)")
        self.pattern2 = re.compile(r"<\s*img.*\s+src\s*=\s*([\'\"])(.+?)\1.*>")
        self.sp = getattr(vonder, using_sp).ServiceProvider()

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
        content = ''
        while True:
            if size > self.read_size:
                read_size = self.read_size
            elif 0 < size <= self.read_size:
                read_size = size
            else:
                break
            content = old_handler.read(read_size)
            new_handler.write(content)
            new_handler.flush()
            size -= self.read_size
        return content

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
                    ret_data = self.sp.upload(abs_path)
                    image_url = ret_data['download_url']
                    print "   ===>Got", image_url
                    seek_end = start
                    self.write_to_new_file(
                        file, new_file, seek_start, seek_end)
                    new_file.write(image_url)
                    seek_start = end
                while True:
                    seek_end = seek_start + self.read_size
                    content = self.write_to_new_file(
                        file, new_file, seek_start, seek_end)
                    seek_start = seek_end
                    if not content:
                        break

        print "===>All Done!"
        print "===>Saved as", new_file_path

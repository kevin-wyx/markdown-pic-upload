# -*- coding: utf-8 -*-
from ConfigParser import SafeConfigParser
import base64
import hashlib
import hmac
import json
import os
import time
import urllib2

from tools import forms


class ServiceProvider(object):
    def __init__(self, file_name_prefix=None, token_expire=3600):
        parser = SafeConfigParser()
        parser.read('server.conf')

        if not parser.has_section('qiniu'):
            print('Please add config of vendor: qiniu')
            return

        self.token_expire = token_expire
        self.secret_key = parser.get('qiniu', 'secret_key')
        self.access_key = parser.get('qiniu', 'access_key')
        self.upload_url = parser.get('qiniu', 'upload_url')
        print('upload_url: %s' % self.upload_url)
        self.bucket_name = parser.get('qiniu', 'bucket_name')
        self.domain_name = parser.get('qiniu', 'domain_name')
        self.file_name_prefix = file_name_prefix \
            or parser.get('qiniu', 'file_name_prefix')
        self.file_name_prefix = None

        self.file_field = 'file'
        self.get_token()
        self.last_token_ts = time.time()

    def is_token_expired(self):
        return time.time() - self.last_token_ts > self.token_expire

    def get_encoded_policy(self, policy):
        policy = json.dumps(policy, separators=(',', ':'))
        policy_encoded = base64.urlsafe_b64encode(policy)
        return policy_encoded

    def get_sign(self, policy_str):
        sign = hmac.new(self.secret_key, bytes(policy_str), hashlib.sha1)\
            .digest()
        encoded_sign = base64.urlsafe_b64encode(sign)
        return encoded_sign

    def get_token(self):
        deadline = int(time.time()) + self.token_expire
        policy = {
            'scope': self.bucket_name,
            'deadline': deadline,
        }
        policy_encoded = self.get_encoded_policy(policy)
        sign = self.get_sign(policy_encoded)

        self.token = '%s:%s:%s' % (self.access_key, sign, policy_encoded)

    def add_upload_form_fileds(self, file_name, custom_fileds=None):
        if self.file_name_prefix:
            key = os.path.join(self.file_name_prefix, file_name)
        else:
            key = file_name
        if self.is_token_expired():
            self.get_token()
        self.upload_form.add_field('token', self.token)
        self.upload_form.add_field('key', key)
        if custom_fileds:
            for k, v in custom_fileds.iteritems():
                self.upload_form.add_field('x:%s' % k, v)

    def make_request(self, url, action, data=None, headers=None):
        if data:
            print 'data: \n%s' % data
            req = urllib2.Request(url, data)
            req.add_header('Content-Length', len(data))
        else:
            req = urllib2.Request(url)
        if action == 'upload':
            req.add_header('Host', 'up-z2.qiniu.com')
            req.add_header('Content-Type', self.upload_form.get_content_type())
            # req.add_data(data)

        if headers:
            for k, v in headers.iteritems():
                req.add_header(k, v)

        req_data = req.get_data()
        print('req_data: \n%s' % req_data)
        print('req_method: %s' % req.get_method())
        print('req_headers: \n%s' % json.dumps(req.headers))
        try:
            rsp = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            print e.reason
            print e.code
            print e.read()
            raise e
        except Exception as e:
            print e.message
            raise e
        ret_data = rsp.read()
        return ret_data

    def upload(self, file_path, mimetype=None):
        self.upload_form = forms.MultiPartForm()
        file_name = file_path.rsplit('/')[-1]
        self.add_upload_form_fileds(file_name)
        with open(file_path, 'rb') as handler:
            self.upload_form.add_file(
                self.file_field, file_name, handler, mimetype)

        body = str(self.upload_form)
        ret_data = self.make_request(self.upload_url, 'upload', data=body)
        data = json.loads(ret_data)
        data['download_url'] = os.path.join(
            self.domain_name.rstrip('/'), data.get('key'))
        return data

#!/usr/bin/python

import socket, os
from os.path import join as joinpath
from pprint import pprint as p
from time import sleep
from traceback import print_exc
from cStringIO import StringIO
import json
from fieldstore import FieldStore
from mpeg import Segmenter, packframes
from urlparse import urlparse

__SIGNATURE__   = 'Ricecast 0.1'

#__DEBUG__   = True
__DEBUG__   = False


def parse_head(head):
    lines   = head.split('\r\n')
    rsp_line    = lines[0]

    fields  = FieldStore()
    for line in lines[1:]:
        name, value = line.split(':', 1)
        fields[name] = value
    return fields




class Source(object):
    def __init__(self, src, segment_duration=10,
            output_dir='.', entry_file='entry.json', mount='', ext=".mp3"):

        s   = urlparse(src)
        self.host   = s.hostname
        self.port   = 80 if s.port is None else s.port
        self.path   = s.path

        self.output_dir = output_dir
        self.ext        = ext
        self.entry_file = entry_file
        self.entry_path = joinpath(output_dir, entry_file)
        self.mount      = mount
        self.segment_duration   = segment_duration  # in seconds

        self.first  = 0     # pointers
        self.last   = 0

    def connect(self):
        print 'Connecting <http://%s:%s%s>...' % (self.host, self.port, self.path)
        self.sock   = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5) # timeout in 5 secs.
        self.sock.connect((self.host, self.port))

        req     = '\r\n'.join([
            'GET %s HTTP/1.0' % self.path,
            'Host: %s:%s' % (self.host, self.port),
            'User-Agent: %s' % __SIGNATURE__,
            '', ''])

        if __DEBUG__:
            print 'Sending request...'
            print '>'*40
            print req
            print '-'*40

        nbytes  = len(req)
        while nbytes > 0:
            sent    = self.sock.send(req)
            nbytes  -= sent

        if __DEBUG__:
            print 'Request sent. Waiting reply...'

        data    = ''
        while '\r\n\r\n' not in data:
            data    += self.sock.recv(4096)

        head, body  = data.split('\r\n\r\n', 1)

        if __DEBUG__:
            print 'Received head'
            print '<'*40
            print head
            print '-'*40

        fields  = parse_head(head)

        self.type   = fields['content-type']
        self.bitrate= int(fields['icy-br'])  # in kbps
        self.name   = fields['icy-name']
        self.url    = fields['icy-url']
        self.server = fields['server']

        print '-'*40
        print 'Name:    %s' % self.name
        print 'URL:     %s' % self.url
        print 'Server:  %s' % self.server
        print 'Type:    %s' % self.type
        print 'Bitrate: %d kbps' % self.bitrate
        print '-'*40
        print 'Ready to record.'


    def segment(self):
        while True:
            data    = self.sock.recv(4096)
            if data == '':  raise socket.error('Source closed.')

            frames  = self.segmenter.feed(data)
            if len(frames) > 0:     # a segment is ready
                return packframes(frames)


    def save_segment(self, segment, cnt):
        filename    = joinpath(self.output_dir, '%d%s' % (cnt, self.ext))
        open(filename, 'wb').write(segment)
        print 'Saved segment #%d at %s' % (cnt, filename)


    def update_entry_file(self, stopped=False):
        entry  = { 
                'name':             self.name, 
                'url':              self.url, 
                'content_type':     self.type,
                'bitrate':          self.bitrate,
                'segment_duration': self.segment_duration,
                'mount':            self.mount,
                'ext':              self.ext,
                'started':          True,
                'stopped':          stopped,
                'first':            self.first,
                'last':             self.last
        }

        open(self.entry_path, 'wb').write(json.dumps(entry))


    def prepare_segment(self, window=None):
        print 'Receiving segment #%d...' % (self.last)
        data    = self.segment()
        self.save_segment(data, self.last)
        if window is not None and (self.last - self.first) >= window:
            # remove aged file
            file2remove    = joinpath(self.output_dir, '%d%s' % (self.first, self.ext))
            os.remove(file2remove)
            print 'Removed segment', file2remove
            self.first  = self.last - window + 1     # sliding window forward
        self.update_entry_file()
        self.last   += 1


    def record(self, window=None):
        while True:
            try:
                self.connect()
                self.segmenter  = Segmenter(self.segment_duration * 1000)    # in milliseconds
                while True:
                    self.prepare_segment(window)
            except socket.error:
                sleep(5)
                print 'Source closed. Reconnecting in 5 seconds...'
            finally:
                self.sock.close()


    def close(self):
        self.update_entry_file(stopped=True)


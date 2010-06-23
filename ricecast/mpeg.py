##########################################
# MPEG Stream Framing and Segmenting
# 
# Author:   Riobard Zhan
# Email:    me@riobard.com
# Web:      http://riobard.com
#
#
# based on info from http://www.mp3-tech.org/
#
##########################################


import struct
from collections import namedtuple


class MPEGHeader(namedtuple('MPEGHeader', ' '.join([
        'version',              # MPEG-1, MPEG-2, MPEG-2.5
        'layer',                # I, II, III
        'nocrc',                # 0, 1
        'bitrate',              # int in kbps = 1000 bits per second
        'samplingrate',         # int in Hz
        'padding',              # 0, 1
        'private',              # 0, 1
        'mode',                 # Single, Joint, Dual, Stereo
        'ext',                  # 0-4; only for Joint stereo mode. detail unreported
        'copyright',            # 0, 1
        'original',             # 0, 1
        'emphasis',             # ['', '50/15 ms', None, 'CCIT J.17']
        'duration',             # in milliseconds
        'length'                # in bytes
    ]))):

    __slots__   = []    # save memory

    # bitrates in kbps; 0 means freeformat
    # MPEG-1, layer I
    BITRATE_V1L1    = [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448]
    # MPEG-1, layer II
    BITRATE_V1L2    = [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384]
    # MPEG-1, layer III
    BITRATE_V1L3    = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
    # MPEG-2/2.5, layer I
    BITRATE_V2L1    = [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256]
    # MPEG-2/2.5, layer II/III
    BITRATE_V2L2    = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
    BITRATE_V2L3    = BITRATE_V2L2

    # NOTE for Layer II there are some bitrate and mode combinations not allowed

    MPEG_BITRATE    = [
            [ None, BITRATE_V2L3, BITRATE_V2L2, BITRATE_V2L1 ], # MPEG-2.5
            None,
            [ None, BITRATE_V2L3, BITRATE_V2L2, BITRATE_V2L1 ], # MPEG-2
            [ None, BITRATE_V1L3, BITRATE_V1L2, BITRATE_V1L1 ]  # MPEG-1
        ]

    MPEG_SAMPLINGRATE   = [  # in Hz
            [11025, 12000, 8000],       # MPEG-2.5
            None,
            [22050, 24000, 16000],      # MPEG-2
            [44100, 48000, 32000]       # MPEG-1
        ]


    @classmethod
    def parse(cls, header):
        ''' parse 4 bytes MPEG header '''

        try:
            # 4-byte unsigned int big-endian
            # NOTE: Intel processors are little-endian
            I   = struct.unpack('!I', header)[0]
        except struct.error:
            return None

        # 11 bits sync word (pos 31-21)
        if (I>>21 != 0b11111111111): return None

        # 2 bits MPEG audio version ID (pos 20-19)
        version_index = (I>>19) & 0b11
        if (version_index == 0b01):   return None
        version    = [
            'MPEG-2.5', # later extension of MPEG-2
            None,       # reserved
            'MPEG-2',   # ISO/IEC 13818-3
            'MPEG-1'    # ISO/IEC 11172-3
        ][version_index]

        # 2 bits layer description (pos 18-17)
        layer_index   = (I>>17) & 0b11
        if (layer_index == 0b00): return None
        layer   = [None, 'III', 'II', 'I'][layer_index]

        # 1 bit protection bit (pos 16)
        nocrc   = (I>>16) & 0b1
        # 0 = protected by CRC (16 bits CRC after header
        # 1 = no CRC protection

        # 4 bits bitrate index (pos 15-12)
        bitrate_index   = (I>>12) & 0b1111
        if (bitrate_index == 0b1111): return None
        bitrate             = cls.MPEG_BITRATE[version_index][layer_index][bitrate_index]
        # NOTE in kbps = 1,000 bit per second

        # 2 bits sampling rate frequence index (pos 11-10)
        samplingrate_index  = (I>>10) & 0b11
        if samplingrate_index == 0b11: return None
        samplingrate        = cls.MPEG_SAMPLINGRATE[version_index][samplingrate_index]

        # 1 bit padding bit (pos 9)
        padding = (I>>9) & 0b1
        # 0: frame is not padded
        # 1: frame is padded with one extra slot

        # Padding is used to fit the bit rates exactly. For an example: 128k
        # 44.1kHz layer II uses a lot of 418 bytes and some of 417 bytes long
        # frames to get the exact 128k bitrate. For Layer I slot is 32 bits long,
        # for Layer II and Layer III slot is 8 bits long.


        # How to calculate frame length
        # 
        # First, let's distinguish two terms frame size and frame length. Frame
        # size is the number of samples contained in a frame. It is constant and
        # always 384 samples for Layer I and 1152 samples for Layer II and Layer
        # III. Frame length is length of a frame when compressed. It is calculated
        # in slots. One slot is 4 bytes long for Layer I, and one byte long for
        # Layer II and Layer III. When you are reading MPEG file you must calculate
        # this to be able to find each consecutive frame. Remember, frame length
        # may change from frame to frame due to padding or bitrate switching.
        # 
        # Read the BitRate, SampleRate and Padding of the frame header.
        # 
        # For Layer I files us this formula:
        # 
        # FrameLengthInBytes = (12 * BitRate / SampleRate + Padding) * 4
        # 
        # For Layer II & III files use this formula:
        # 
        # FrameLengthInBytes = 144 * BitRate / SampleRate + Padding
        # 
        # Example: Layer III, BitRate=128000, SampleRate=441000, Padding=0 ==>
        # FrameSize=417 bytes


        # frame length in bytes (including 4 bytes header)
        if layer == 0b11:   # Layer I
            frame_length    = (12 * bitrate * 1000 / samplingrate + padding) * 8
            duration        = 384 / (samplingrate / 1000.0)     # in milliseconds
        else: # Layer II/III
            frame_length    = 144 * bitrate * 1000 / samplingrate + padding
            duration        = 1152 / (samplingrate / 1000.0)    # in milliseconds

        #if not nocrc: frame_length    += 2  
        # 2 bytes (16 bits) CRC after header
        # QUESTION: should this count as frame length?

        if frame_length == 0: return None

        # 1 bit private bit (pos 8)
        private = (I>>8) & 0b1
        # only informative; no use. It may be freely used for specific needs of an
        # application, i.e. if it has to trigger some application specific events.


        # 2 bits channel mode (pos 7-6)
        mode_index    = (I>>6) & 0b11
        mode    = [
            'Stereo', 
            'Joint',    # joint stereo
            'Dual',     # 2 mono channels (separate)
            'Single'    # 1 mono channel
        ][mode_index]

        # 2 bits channel mode extension (pos 5-4)
        ext    = (I>>4) & 0b11
        # only for Joint stereo mode

        # 1 bit copyright (pos 3)
        copyright   = (I>>3) & 0b1
        # 0 = audio is not copyrighted
        # 1 = audio is copyrighted; illegal to copy

        # 1 bit original (pos 2)
        original    = (I>>2) & 0b1
        # 0 = copy of original media
        # 1 = original media

        # 2 bit emphasis (pos 1-0)
        emphasis    = I & 0b11
        if (emphasis == 0b10): return None
        emphasis    = ['', '50/15 ms', None, 'CCIT J.17'][emphasis]

        # The emphasis indication is here to tell the decoder that the file must be
        # de-emphasized, ie the decoder must 're-equalize' the sound after a
        # Dolby-like noise supression. It is rarely used.

        return MPEGHeader(version, layer , nocrc, bitrate, samplingrate, padding, private, 
                mode, ext, copyright, original, emphasis , duration, frame_length)




class MPEGFrame(object):
    __slots__ = ['header', 'data']      # save memory

    def __init__(self, header, data):
        self.header = header
        self.data   = data

    def __repr__(self):
        return 'MPEGFrame(header=%s, data=<%d bytes>)' % (repr(self.header), len(self.data))

    def __getattr__(self, name):
        # access header attributes directly
        return self.header.__getattribute__(name)


class Framer(object):
    ''' Incrementally parse a stream and produce frames '''

    def __init__(self):
        self.buf        = ''
        self.frames     = []
        self.last_frame = None  # partial frame if not None


    def feed_last_frame(self, chunk):
        if self.last_frame is not None and len(chunk) > 0:
            r   = self.last_frame.length - len(self.last_frame.data)
            if r <= len(chunk):  # last frame now complete
                rest, chunk  = chunk[:r], chunk[r:]
                #print 'last frame:', repr(self.last_frame), len(self.last_frame.data)
                self.last_frame.data += rest
                self.frames.append(self.last_frame)
                self.last_frame = None
            else:   # last frame still pending
                self.last_frame.data    += chunk
                chunk   = ''

        return chunk



    def parse_frame(self, chunk):
        i   = chunk.find('\xff')
        while i != -1:      # check all \xff
            header  = MPEGHeader.parse(chunk[i:i+4])
            if header is None:     # not a valid header
                i   = chunk.find('\xff', i+1)   # next \xff
            else:       # valid header
                garbage = chunk[:i]     # might contain garbage after the last frame
                if len(chunk[i:]) >= header.length:    # the frame is complete
                    frame   = MPEGFrame(header=header, data=chunk[i:i+header.length])
                    return garbage, frame, chunk[i+header.length:]   # and rest of the stream
                else:   # only part of the frame is available in the chunk
                    self.last_frame = MPEGFrame(header=header, data=chunk[i:])
                    return garbage, None, None



    def feed(self, chunk):
        # leftover of last frame
        chunk   = self.feed_last_frame(chunk)

        if len(self.buf) + len(chunk) < 4:  # require at least 4 bytes to get the header
            self.buf    += chunk
            return []

        chunk   = self.buf + chunk
        self.buf    = ''
        res = self.parse_frame(chunk)

        if res is None: # chunk is completely garbage
            print '-'*40
            print len(chunk), 'bytes garbage chunk'
            pass
        else:   # tuple:
            _, frame, rest  = res
            if len(_) > 0:
                print len(_), 'bytes garbage before frame'
            if frame is None:   # partial frame
                #print '-'*40
                #print 'Partial frame, header=', self.last_frame
                pass
            else:
                #print '-'*40
                #print 'Complete frame = ', frame
                self.frames.append(frame)
                return self.feed(rest)


        frames  = self.frames
        self.frames  = []
        return frames




class Segmenter(object):
    def __init__(self, duration=1000):
        self.framer     = Framer()
        self.duration   = duration   # max segment duration in milliseconds

        self.buf           = []
        self.buf_duration  =  0


    def feed(self, chunk):
        frames  = self.framer.feed(chunk)
        segment = []
        for frame in frames:
            if self.buf_duration + frame.duration > self.duration:
                # segment ready
                segment = self.buf
                self.buf            = []
                self.buf_duration   = 0
            else:   # accumulating frames for the current segment
                self.buf.append(frame)
                self.buf_duration   += frame.duration


        return segment


    def done(self):
        ''' get any accumulated frames and the last partial frame if any '''

        if self.framer.last_frame is not None:
            segment = self.buf + [self.framer.last_frame]
            self.buf    = []
        else:
            segment = self.buf
            self.buf    = []

        return segment



def packframes(frames):
    return ''.join(frame.data for frame in frames)

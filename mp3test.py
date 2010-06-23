from ricecast import Framer, Segmenter, packframes
from pprint import pprint as p


from sys import argv
f   = open(argv[1])



'''
frames  = []
s   = Framer()
frames.extend(s.feed(f.read(400)))
frames.extend(s.feed(f.read(800)))
frames.extend(s.feed(f.read(1200)))
frames.extend(s.feed(f.read(1600)))
frames.extend(s.feed(f.read()))

p(frames)
#raw = ''.join(frame.data for frame in frames)
#print s.last_frame
#open(argv[1]+'.frames', 'wb').write(raw)
'''

s   = Segmenter(1000)
res = []
res = s.feed(f.read(400))
p(res)
res = s.feed(f.read(800))
p(res)
res = s.feed(f.read(1200))
p(res)
res = s.feed(f.read(2400))
p(res)
res = s.feed(f.read(4800))
p(res)
res = s.feed(f.read(4800))
p(res)
res = s.feed(f.read(4800))
p(res)
res = s.feed(f.read(4800))
p(res)
res = s.feed(f.read(4800))
p(res)
res = s.feed(f.read(4800))
p(res)
res = s.feed(f.read())
p(res)
res = s.done()
p(res)

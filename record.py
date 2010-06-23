from ricecast import Source


'''
src = Source(src="http://blogfiles.wfmu.org/DG/stream3.php",
        output_dir="wfmu/", segment_duration=10,
        entry_file="entry.json",
        mount="wfmu")
src = Source(
        src='http://localhost:8000/listen', 
        segment_dir='segment/', 
        segment_duration=10,
        entry_file='segment/entry.json', 
        mount='')
'''

src = Source(
        src="http://glb-stream11.streaming.init7.net/2/rsj/mp3_128",
        segment_duration=10,
        output_dir="jazz", entry_file="entry.json", 
        mount="jazz/", ext=".mp3")

try:
    src.connect()
    src.record(window=6)
except KeyboardInterrupt:
    pass
except:
    raise
finally:
    src.close()

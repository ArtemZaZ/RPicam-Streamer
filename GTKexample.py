import time
import receiver

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from PIL import Image

IP_ROBOT = '173.1.0.86'
RTP_PORT = 5000

recv = receiver.StreamReceiver(receiver.FORMAT_H264, (IP_ROBOT, RTP_PORT), True)
recv.play_pipeline()

try:
    while True:
        if recv.imageBuf:
            print(recv.imageBuf[0], recv.imageBuf[1], len(recv.imageBuf[2]))
            try:
                image = Image.frombytes("RGB", [recv.imageBuf[0], recv.imageBuf[1]], recv.imageBuf[2], "raw", "RGB")
                print(image)
            except:
                print("NO")
        time.sleep(0.1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

recv.stop_pipeline()
recv.null_pipeline()

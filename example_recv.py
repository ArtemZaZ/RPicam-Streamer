#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import receiver

IP_ROBOT = '173.1.0.86'
RTP_PORT = 5000

recv = receiver.StreamReceiver(receiver.FORMAT_H264, (IP_ROBOT, RTP_PORT), True)
recv.play_pipeline()

# главный цикл программы
try:
    while True:
        if recv.imageBuf:
            print(recv.imageBuf[0])
        time.sleep(0.1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

recv.stop_pipeline()
recv.null_pipeline()

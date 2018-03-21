#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
import sys
gi.require_version('Gst', '1.0')
from gi.repository import Gst

FORMAT_H264 = 0
FORMAT_MJPEG = 1

RTP_PORT = 5000
HOST = '127.0.0.1'


class StreamReceiver(object):
    def __init__(self, video=FORMAT_H264, host=(HOST, RTP_PORT), toAppSink=False):
        self.imageBuf = None    # Выходное изображение из app-sink
        self._host = host
        Gst.init(None)  # инициализация Gstreamer
        self.make_pipeline(video, host, toAppSink)     # создаем pipeline

        self.bus = self.pipeline.get_bus()  # подключаем обработчик сообщений
        self.bus.add_signal_watch()
        self.bus.connect('message', self.onMessage)

        self.ready_pipeline()   # запускаем pipeline

    def make_pipeline(self, video, host, toAppSink):
        self.pipeline = Gst.Pipeline()  # Создание GStreamer pipeline

        rtpbin = Gst.ElementFactory.make('rtpbin')  # rtpbin
        rtpbin.set_property('autoremove', True)
        rtpbin.set_property('latency', 200)
        rtpbin.set_property('drop-on-latency', True)    # отбрасывать устаревшие кадры
        rtpbin.set_property('buffer-mode', 0)

        formatStr = 'H264'  # RTP Video
        payloadType = 96

        if video:
            videoStr = 'JPEG'
            payloadType = 26

        srcCaps = Gst.Caps.from_string('application/x-rtp, media=video,clock-rate=90000, encoding-name=%s, payload=%d' % (formatStr, payloadType))

        udpsrc_rtpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtpin')
        udpsrc_rtpin.set_property('port', host[1])
        udpsrc_rtpin.set_property('caps', srcCaps)

        udpsrc_rtcpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtcpin')
        udpsrc_rtcpin.set_property('port', host[1] + 1)

        udpsink_rtcpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtcpout')
        udpsink_rtcpout.set_property('host', host[0])
        udpsink_rtcpout.set_property('port', host[1] + 5)
        udpsink_rtcpout.set_property('sync', False)
        udpsink_rtcpout.set_property('async', False)

        depayName = 'rtph264depay'
        decoderName = 'avdec_h264' # хреново работает загрузка ЦП 120%
        if video:
            depayName = 'rtpjpegdepay'
            decoderName = 'jpegdec' #

        depay = Gst.ElementFactory.make(depayName)  # depayloader

        decoder = Gst.ElementFactory.make(decoderName)  # decoder
        videorate = Gst.ElementFactory.make('videorate')

        videoconvert = Gst.ElementFactory.make('videoconvert')
        if toAppSink:   # если устновлен флаг линковки с app-sink

            def toImageBuf(sample):
                buf = sample.get_buffer()
                icaps = sample.get_caps()
                arr = [
                    icaps.get_structure(0).get_value('width'),
                    icaps.get_structure(0).get_value('height'),
                    buf.extract_dup(0, buf.get_size())]
                return arr

            def new_buffer(sink, data):  # callback функция, исполняющаяся при каждом приходящем кадре
                sample = sink.emit("pull-sample")
                self.imageBuf = toImageBuf(sample)
                return Gst.FlowReturn.OK

            sink = Gst.ElementFactory.make("appsink")
            caps = Gst.caps_from_string("video/x-raw, format=(string){RGB}")   # формат синка
            sink.set_property("caps", caps)
            sink.set_property("emit-signals", True)
            sink.connect("new-sample", new_buffer, sink)
        else:
            sink = Gst.ElementFactory.make('autovideosink')     # sink
            sink.set_property('sync', False)

        elemList = [rtpbin, depay, decoder, videorate, videoconvert, sink, udpsrc_rtpin,  # добавляем все элементы в pipeline
                    udpsrc_rtcpin, udpsink_rtcpout]

        for elem in elemList:
            self.pipeline.add(elem)

        ret = depay.link(decoder)   # соединяем элементы
        ret = ret and decoder.link(videorate)
        ret = ret and videorate.link(videoconvert)
        ret = ret and videoconvert.link(sink)

        # соединяем элементы rtpbin

        def PadAdded(rtpbin, new_pad, gstElem):
            sinkPad = Gst.Element.get_static_pad(gstElem, 'sink')
            res = (Gst.Pad.link(new_pad, sinkPad) == Gst.PadLinkReturn.OK)

        def PadLink(src, name):
            srcPad = Gst.Element.get_static_pad(src, 'src')
            sinkPad = Gst.Element.get_request_pad(rtpbin, name)
            return Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK

        ret = ret and udpsrc_rtpin.link_pads('src', rtpbin, 'recv_rtp_sink_0')
        ret = ret and udpsrc_rtcpin.link_pads('src', rtpbin, 'recv_rtcp_sink_0')
        ret = ret and rtpbin.link_pads('send_rtcp_src_0', udpsink_rtcpout, 'sink')

        if not ret:
            print('ERROR: Elements could not be linked')
            sys.exit(1)

        rtpbin.connect('pad-added', PadAdded, depay) # динамическое подключение rtpbin->depay

    def onMessage(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            print('Received EOS-Signal')
            self.stop_pipeline()
        elif t == Gst.MessageType.ERROR:
            print('Received Error-Signal')
            error, debug = message.parse_error()
            print('Error-Details: #%u: %s' % (error.code, debug))
            self.null_pipeline()

    def getStatePipeline(self):
        state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE).state
        print('GST pipeline', state)


    def play_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        print('GST pipeline PLAYING')

    def stop_pipeline(self):
        self.pause_pipeline()
        self.ready_pipeline()

    def ready_pipeline(self):
        self.pipeline.set_state(Gst.State.READY)
        print('GST pipeline READY')

    def pause_pipeline(self):
        self.pipeline.set_state(Gst.State.PAUSED)
        print('GST pipeline PAUSED')

    def null_pipeline(self):
        print('GST pipeline NULL')
        self.pipeline.set_state(Gst.State.NULL)


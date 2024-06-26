"""Nuand BladeRF Frequency Scanner Server

This module contains the frequency scanner server. It opens the
device, randomly samples the frequency range, and queues the
output. When a client connects over TCP the queued up measurements
are sent without waiting for an acknowledgement.
"""
import argparse
import socket
import threading
import queue
import yaml
import bladerf
from lib.bladeandnumpy import BladeRFAndNumpy
import lib.bsocket as bsocket
import random
import numpy as np
import time
import scipy.signal as signal

def secondary(
    serial: str,
    config_path: str,
    sps: int,
    bw: float,
    args: any) -> None:
    """The main entry function.

    This is called after arguments are parsed.
    """
    with open(config_path, 'r') as fd:
        cfg = yaml.unsafe_load(fd)
    cfg = cfg['servers'][serial]

    dev = BladeRFAndNumpy(f'libusb:serial={serial}')

    num_buffers = 16
    buffer_size = 1024 * 8
    buffer_samps = num_buffers * buffer_size

    dev.sync_config(
        bladerf.ChannelLayout.RX_X2,
        bladerf.Format.SC16_Q11,
        num_buffers=num_buffers,
        buffer_size=buffer_size,
        num_transfers=8,
        stream_timeout=20000
    )

    dev.enable_module(0, True)
    dev.enable_module(2, True)

    msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    msock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print('binded', cfg['host'], cfg['port'])
    msock.bind((cfg['host'], cfg['port']))
    msock.listen(1)

    rx_data_q = queue.Queue()

    core_th = threading.Thread(
        target=core,
        args=(
            msock, dev, rx_data_q
        )
    )
    core_th.start()

    rx_thread(
        cfg,
        dev,
        rx_data_q,
        num_buffers,
        buffer_size,
        sps,
        bw,
        args
    )

def core(msock, dev, rx_data_q):
    """The TCP client core loop.

    This function handles exceptions from the client.
    """
    while True:
        sock, _addr = msock.accept()
        try:
            _inner(
                sock,
                dev,
                rx_data_q
            )
        except bsocket.SocketException:
            print('socket exception')
        except ConnectionResetError:
            print('connection reset error')
        except BrokenPipeError:
            print('broken pipe error')

def _inner(sock, dev, rx_data_q):
    """The core client loop function.

    This is a simple function that moves data from
    the queue to the client.
    """
    while True:
        ret = rx_data_q.get()
        print('sending')
        bsocket.send_pickle(sock, ret)

def rx_thread(
        cfg: dict[any, any],
        dev: BladeRFAndNumpy,
        rx_data_q: queue.Queue,
        num_buffers: int,
        buffer_size: int,
        sps: int,
        bw: float,
        args: any):
    """Receives samples from the device and queues the output.

    This function tunes the device, sets configurations, queries
    for samples, computes the output, and places the output in
    a queue.
    """
    buffer_mul = 4
    buffer_samps = int(num_buffers * buffer_size // 8 * buffer_mul)
    void = bytes(buffer_samps * 8)

    if bw is None:
        bw = 200e3

    for ch in [0, 2]:
        dev.set_gain_mode(ch, bladerf.GainMode.Manual)
        dev.set_bias_tee(ch, False)
        dev.set_frequency(ch, 70e6)
        dev.set_bandwidth(ch, bw)
        dev.set_sample_rate(ch, sps)
        dev.set_gain(ch, 60)
        dev.enable_module(ch, True)

    samp_count = 25000

    if args.channel_bw is not None:
        slide_cnt = int(sps / args.channel_bw)
        t = samp_count / sps
        shifter = np.exp(1j * np.linspace(
            0, np.pi * 2 * -args.channel_bw * t, samp_count
        ))
        shifter_filter = signal.butter(8, args.channel_bw, btype='low', output='sos', fs=sps)

    while True:
        freq = random.randint(
            int(float(cfg['freq-min'])), 
            int(float(cfg['freq-max']))
        )
        dev.set_frequency(0, freq)
        dev.sample_as_f64(buffer_samps, 2, 4, 0)
        b0, b1 = dev.sample_as_f64(samp_count, 2, 4, 0)
        b0m = np.mean(np.abs(b0))
        b1m = np.mean(np.abs(b1))

        if args.channel_bw is not None:
            dbg = []
            cout = []
            b0b = b0.copy()
            b1b = b1.copy()
            for slide_ndx in range(slide_cnt):
                cur_center = slide_ndx * args.channel_bw
                if cur_center > sps * 0.5:
                    cur_center = -(sps * 0.5) + (cur_center - sps * 0.5)
                b0bf = np.mean(np.abs(signal.sosfilt(shifter_filter, b0b)))
                b1bf = np.mean(np.abs(signal.sosfilt(shifter_filter, b1b)))
                cout.append({
                    'freq': cur_center,
                    'b0': b0bf,
                    'b1': b1bf,
                })
                b0b *= shifter
                b1b *= shifter                
        else:
            cout = None

        while rx_data_q.qsize() > 100:
            time.sleep(0)

        print('loaded', freq, b0m, b1m)
        rx_data_q.put({
            'time': time.time(),
            'freq': freq, 
            'b0': b0m, 
            'b1': b1m, 
            'bw': bw,
            'sps': sps,
            'channel': cout,
        })

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=str, required=True)
    ap.add_argument('--serial', type=str, required=True)
    sps_help = 'This is the samples per second used to sample. This is the bandwidth of the baseband.'
    ap.add_argument('--sps', type=int, default=int(1e6), help=sps_help)
    bw_help = 'This controls the width of the chunks the baseband is broken down into as each of these are a sample. If no value is specified then the bandwidth is equal to 200e3.'
    ap.add_argument('--bw', type=float, default=None, help=bw_help)
    cbw_help = 'This controls the channel bandwidth. If specified the baseband is broken down into channels.'
    ap.add_argument('--channel-bw', type=float, default=None, help=cbw_help)
    args = ap.parse_args()
    secondary(args.serial, args.config, args.sps, args.bw, args)
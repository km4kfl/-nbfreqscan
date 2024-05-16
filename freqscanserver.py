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

def secondary(serial, config_path):
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

    rx_thread(cfg, dev, rx_data_q, num_buffers, buffer_size)

def core(msock, dev, rx_data_q):
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
    while True:
        ret = rx_data_q.get()
        print('sending', ret)
        bsocket.send_pickle(sock, ret)

def rx_thread(
        cfg,
        dev: BladeRFAndNumpy,
        rx_data_q,
        num_buffers,
        buffer_size):
    
    buffer_mul = 4
    buffer_samps = int(num_buffers * buffer_size // 8 * buffer_mul)
    void = bytes(buffer_samps * 8)

    for ch in [0, 2]:
        dev.set_gain_mode(ch, bladerf.GainMode.Manual)
        dev.set_bias_tee(ch, False)
        dev.set_frequency(ch, 70e6)
        dev.set_bandwidth(ch, 200e3)
        dev.set_sample_rate(ch, 1e6)
        dev.set_gain(ch, 60)
        dev.enable_module(ch, True)

    samp_count = 25000

    while True:
        freq = random.randint(
            int(float(cfg['freq-min'])), 
            int(float(cfg['freq-max']))
        )
        dev.set_frequency(0, freq)
        dev.sample_as_f64(buffer_samps, 2, 4, 0)
        b0, b1 = dev.sample_as_f64(samp_count, 2, 4, 0)
        b0 = np.mean(np.abs(b0))
        b1 = np.mean(np.abs(b1))
        while rx_data_q.qsize() > 100:
            time.sleep(0)
        print('loaded', freq, b0, b1)
        rx_data_q.put((time.time(), freq, b0, b1))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=str, required=True)
    ap.add_argument('--serial', type=str, required=True)
    args = ap.parse_args()
    secondary(args.serial, args.config)
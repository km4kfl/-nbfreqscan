"""Connects to the signal servers, uploads TX data, schedules
TX and RX times, downloads RX data, and returns RX data.

This is a very simple module. It reads a YAML file for the
configuration of servers. It requires the samples per second,
frequency, and any TX signals or `None`. Each server gets
two `tx_signals` entries for each antenna. This was designed
with the BladeRF A4 which has two transmit channels.
"""
import yaml
import socket
import lib.bsocket as bsocket
import time
import pickle

def execute(config_path: str):
    with open(config_path, 'r') as fd:
        cfg = yaml.unsafe_load(fd)
    
    sec = cfg['servers']

    socks = []
    socks_ndx = []

    k_ndx = 0
    for k in sec:
        scfg = sec[k]
        if not scfg['enabled']:
            #print('disabled', scfg['host'], scfg['port'])
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #print('connecting', scfg['host'], scfg['port'])
        try:
            print('connecting', scfg['host'], scfg['port'])
            sock.connect((scfg['host'], scfg['port']))
            print('connected')
            socks.append(sock)
            socks_ndx.append(k_ndx)
        except ConnectionRefusedError as e:
            print('connection refused', scfg['host'], scfg['port'])
        k_ndx += 1

    fd = open('plot', 'ab')

    print('reading')
    while True:
        for ndx, sock in enumerate(socks):
            mt, freq, b0, b1 = bsocket.recv_pickle(sock)
            pickle.dump((
                mt, freq, b0, b1, socks_ndx[ndx]
            ), fd)
            fd.flush()
            print(mt, freq, b0, b1, socks_ndx[ndx])

if __name__ == '__main__':
    execute('config.yaml')
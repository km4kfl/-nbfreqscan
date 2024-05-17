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
import argparse

def execute(config_path: str):
    """Yields measurements.

    The configuration specifies how to connect to the sources and what
    sources. This function yeilds, as a generator, the measurements
    and the source index. One may need to directly read the configuration
    to relate the source index back to specific parameters if needed.
    """
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

    print('reading')
    while True:
        for ndx, sock in enumerate(socks):
            data = bsocket.recv_pickle(sock)
            yield data, socks_ndx[ndx]

def main(config_path: str, data_output_path: str):
    """The main entry point of the program.

    If this module is called directly this will read the
    configuration, gather measurements, and write them to
    the `data_output_path` specified.
    """
    fd = open(data_output_path, 'ab')

    for data, source_ndx in execute(config_path):
        mt, freq = data['time'], data['freq']
        b0, b1 = data['b0'], data['b1']
        pickle.dump((
            mt, freq, b0, source_ndx
        ), fd)
        fd.flush()
        print(mt, freq, b0, b1, source_ndx)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=str, default='config.yaml')
    ap.add_argument('--output', type=str, default='plot')
    args = ap.parse_args()
    main(args.config, args.output)
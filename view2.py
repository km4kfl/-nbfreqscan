import numpy as np
import pickle
import time
import matplotlib.pyplot as plt
import matplotlib.colors as cmap
import datetime as dt
import scipy.ndimage as ndimage
import scipy.signal as signal
import os
import argparse
import threading
import queue
import matplotlib.dates as mdates

def enumerate_samples():
    with open('s3radio248.pickle', 'rb') as fd:
        try:
            while True:
                key, blob = pickle.load(fd)
                for sample in blob:
                    src_ndx = sample['src_ndx']
                    sample = sample['data']
                    freq = sample['freq']
                    if 'channel' in sample:
                        channel = sample['channel']
                        for item in channel:
                            offset = item['freq']
                            b0, b1 = item['b0'], item['b1']
                            item_freq = freq + offset
                            yield item_freq, b1
        except EOFError:
            pass

def build_index(path, indices=None):
    """Build the index from scratch or use existing index data.

    If using existing index data, through `indices`, then the existing data
    must have had the new data appended.
    """
    print('[building index] %s --> %s' % (path, path + '.index2'))
    fd = open(path, 'rb')
    fdx = open(path + '.index2', 'wb')

    msz = fd.seek(0, 2)
    fd.seek(0)

    if indices is not None:
        fd.seek(indices[-1][1])
    else:
        indices = []

    ilt = time.time()

    while True:
        if time.time() - ilt > 5:
            ilt = time.time()
            per_done = fd.tell() / msz * 100.0
            print('[building index..] %.2f%%' % per_done)
        fd_pos = fd.tell()
        try:
            key, blob = pickle.load(fd)
        except EOFError:
            break
        ts = key[1]
        indices.append((
            ts,
            fd_pos,
        ))
    print('saving index to disk')
    pickle.dump(indices, fdx)
    fd.close()
    fdx.close()

def rebuild_index(path):
    """Rebuilds the index when new data has been appended.
    
    Read the existing index and use it to shorten the time to rebuild the
    index for data appended. If the data was created new or data changed that
    existed when the index was created then this function won't work correctly.
    """
    index_path = path + '.index2'
    with open(index_path, 'rb') as fd:
        indices = pickle.load(fd)
    build_index(path, indices)

def enumerate_channel(data_path, status_prefix, dtl_start, dtl_end):
    print(status_prefix)

    def generator_func(dtl_start, dtl_end):
        index2_path = '%s.index2' % data_path
        if not os.path.exists(index2_path):
            build_index(data_path)

        if os.stat(data_path).st_mtime > os.stat(index2_path).st_mtime:
            rebuild_index(data_path)

        with open(index2_path, 'rb') as fd:
            indices = pickle.load(fd)

        indices.sort(key=lambda item: item[0])
        
        lti = time.time()

        with open(data_path, 'rb') as fd:
            for ndx, (ts, fd_pos) in enumerate(indices):
                if time.time() - lti > 5:
                    lti = time.time()
                    prog = ndx / (len(indices) - 1) * 100.0
                    print('[%s] %.2f' % (status_prefix, prog))
                if dtl_start is not None and ts < dtl_start:
                    continue
                if dtl_end is not None and ts > dtl_end:
                    continue

                fd.seek(fd_pos)
                key, blob = pickle.load(fd)
                yield blob

    if dtl_start is not None:
        dtl_start = dtl_start.timestamp()
    
    if dtl_end is not None:
        dtl_end = dtl_end.timestamp()

    for blob in generator_func(dtl_start, dtl_end):
        for sample in blob:
            src_ndx = sample['src_ndx']
            if src_ndx != 0:
                continue
            sample = sample['data']
            freq = sample['freq']
            ts = sample['time']
            if 'channel' in sample:
                channel = sample['channel']
                points = np.zeros(len(channel), np.float64)
                freqs = np.zeros(len(channel), np.float64)
                for ndx, item in enumerate(channel):
                    points[ndx] = item['b1']
                    freqs[ndx] = item['freq'] + freq
                yield ts, points, freqs


def build_mask(args):
    """Writes out a spectral mask in the form of coeffients multiplied with each channel.

    The baseband output from the mixer is distorted and attenuated. This tries to estimate
    the attenuation/response and then calculates a sequence of coefficients to equalize the
    frequency response. This way channels can be compared with each other in terms of 
    magnitude.

    The resulting mask can be multiplied by the channel whereby the channel.
    """
    if args.start is not None:
        args_start = dt.datetime.strptime(args.start, '%m/%d/%y %H:%M:%S')
    else:
        args_start = None
    
    if args.end is not None:
        args_end = dt.datetime.strptime(args.end, '%m/%d/%y %H:%M:%S')
    else:
        args_end = None

    s = None
    sc = 0
    st = time.time()
    for _, c, _ in enumerate_channel(args.data, 'building mask...', args_start, args_end):
        if s is None:
            s = c
            sc = 1
        else:
            s += c
            sc += 1

    s /= sc

    smi = np.argmax(s)
    mask = s[smi] / s

    plt.title('Response Along Mixer Output In Frequency')
    plt.plot(s)
    plt.show()
    
    plt.title('Corrective Mask / Coefficients for Channels')
    plt.plot(mask)
    plt.show()
    
    with open('spectral-mask.pickle', 'wb') as fd:
        pickle.dump(mask, fd)


def load_mask():
    """Loads the spectral mask.
    """
    with open('spectral-mask.pickle', 'rb') as fd:
        return pickle.load(fd)

def sigma_plot(args):
    mask = load_mask()

    ts_least = None
    ts_most = None
    f_least = None
    f_most = None

    if args.start is not None:
        args_start = dt.datetime.strptime(args.start, '%m/%d/%y %H:%M:%S')
    else:
        args_start = None
    
    if args.end is not None:
        args_end = dt.datetime.strptime(args.end, '%m/%d/%y %H:%M:%S')
    else:
        args_end = None

    for ts, c, f in enumerate_channel(args.data, 'scanning data for bounds...', args_start, args_end):
        if ts_least is None or ts < ts_least:
            ts_least = ts
        if ts_most is None or ts > ts_most:
            ts_most = ts
        for x in range(len(c)):
            if f_least is None or f[x] < f_least:
                f_least = f[x]
            if f_most is None or f[x] > f_most:
                f_most = f[x]
        size_c = len(c)

    f_delta = f_most - f_least
    ts_delta = ts_most - ts_least

    #
    time_period = args.time_period
    time_period_high_index = int((ts_most - ts_least) / time_period)
    time_period_count = time_period_high_index + 1
    period_resolution = min(time_period_count, args.time_period_max_res)
    freq_bins = args.freq_res

    time_period_marks = np.linspace(ts_least, ts_most, period_resolution)
    time_period_marks = [dt.datetime.fromtimestamp(v) for v in time_period_marks]

    # mean per channel
    mpc = np.zeros((freq_bins, 2), np.float64)

    for ts, c, cf in enumerate_channel(args.data, 'calculating mean energy per channel...', args_start, args_end):
        #ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))
        c *= mask
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        f_pos = f_pos.astype(np.uint32)
        mpc[f_pos, 0] += c
        mpc[f_pos, 1] += 1.0

    mpc = mpc[:, 0] / mpc[:, 1]

    # sum per channel
    spc = np.zeros((freq_bins, 2), np.float64)

    for ts, c, cf in enumerate_channel(args.data, 'calculating standard deviation per channel...', args_start, args_end):
        #ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))
        c *= mask
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        f_pos = f_pos.astype(np.uint32)
        spc[f_pos, 0] += (c - mpc[f_pos]) ** 2
        spc[f_pos, 1] += 1.0

    # std deviation per channel
    stdpc = np.sqrt(spc[:, 0] / spc[:, 1])

    sigma = np.zeros((freq_bins, period_resolution), np.float64)
    m_energy = np.zeros((freq_bins, period_resolution), np.float64)

    for ts, c, cf in enumerate_channel(args.data, 'calculating sigma per channel...', args_start, args_end):
        c *= mask

        ts_pos = np.round((ts - ts_least) / ts_delta * (period_resolution - 1))
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        ts_pos = ts_pos.astype(np.uint32)
        f_pos = f_pos.astype(np.uint32)
        
        if args.only_positive_sigma:
            a = np.abs((c - mpc[f_pos]) / stdpc[f_pos])
        else:
            a = (c - mpc[f_pos]) / stdpc[f_pos]

        try:
            if not args.only_positive_sigma:
                for u in range(len(a)):
                    if np.abs(a[u]) > np.abs(sigma[f_pos[u], ts_pos]):
                        sigma[f_pos[u], ts_pos] = a[u]
            else:
                sigma[f_pos, ts_pos] = np.max(
                    [a, sigma[f_pos, ts_pos]],
                    axis=0
                )

            m_energy[f_pos, ts_pos] = np.max(
                [c, m_energy[f_pos, ts_pos]],
                axis=0
            )
        except IndexError:
            print('index error', f_pos, ts_pos, sigma.shape)

    with open(args.sigma_pickle, 'wb') as fd:
        pickle.dump(sigma, fd)

    with open(args.energy_pickle, 'wb') as fd:
        pickle.dump(m_energy, fd)

    with open('times.pickle', 'wb') as fd:
        pickle.dump(time_period_marks, fd)


def main(args):
    if args.build_mask:
        print('building channel spectral mask')
        build_mask(args)

    if args.build:
        sigma_plot(args)

    with open(args.sigma_pickle, 'rb') as fd:
        sigma = pickle.load(fd)

    with open(args.energy_pickle, 'rb') as fd:
        m_energy = pickle.load(fd)

    with open('times.pickle', 'rb') as fd:
        time_period_marks = pickle.load(fd)

    time_period_marks = mdates.date2num(time_period_marks)

    # def entry(args, m_energy, sigma, time_period_marks):
    __import__('modules.' + args.module, fromlist=['modules']).entry({
        'args': args,
        'm_energy': m_energy, 
        'sigma': sigma,
        'time_period_marks': time_period_marks,
    })
        
if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Displays graphics based on radio survey data.'
    )
    ap.add_argument('--data', type=str, default='s3radio248.pickle')
    # dtl = dt.datetime(2024, 5, 18, 14, 23, 0)
    ap.add_argument('--start', type=str, default='5/18/24 00:00:00')
    ap.add_argument('--end', type=str, default=None)
    ap.add_argument('--build-mask', action=argparse.BooleanOptionalAction)
    ap.add_argument('--freq-res', type=int, default=4096)
    ap.add_argument('--time-period', type=int, default=3600)
    ap.add_argument('--log', type=float, default=1.0)
    ap.add_argument('--pat-x', type=int, default=1)
    ap.add_argument('--pat-y', type=int, default=1)
    ap.add_argument('--time-period-max-res', type=int, default=4096)
    ap.add_argument('--sigma-pickle', type=str, default='sigma.pickle')
    ap.add_argument('--energy-pickle', type=str, default='m_energy.pickle')
    ap.add_argument('--only-positive-sigma', default=False, action=argparse.BooleanOptionalAction)
    ap.add_argument('--build', default=True, action=argparse.BooleanOptionalAction)
    ap.add_argument('--module', type=str, required=True, choices=['humidity', 'energysigma'])
    main(ap.parse_args())
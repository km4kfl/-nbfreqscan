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


def enumerate_channel(status_prefix, dtl_start, dtl_end):
    def read_worker():
        last_print = time.time()
        z = 0
        with open('s3radio248.pickle', 'rb') as fd:
            fd.seek(0, 2)
            msz = fd.tell()
            fd.seek(0)
            try:
                while True:
                    if time.time() - last_print > 5:
                        last_print = time.time()
                        scanned_percentage = fd.tell() / msz * 100.0
                        print('[%s] %.2f' % (status_prefix, scanned_percentage))
                    key, blob = pickle.load(fd)
                    if dtl_start is not None and key[1] < dtl_start:
                        continue
                    if dtl_end is not None and key[1] > dtl_end:
                        continue
                    q.put(blob)
                    z += 1
                    #if z > 20:
                    #    break
            except EOFError:
                pass        
        q.put(None)

    #dtl = dt.datetime(2024, 5, 18, 14, 23, 0)
    #dtl = dt.datetime(2024, 6, 25, 0, 0, 0)
    #dtl = dtl.timestamp()
    if dtl_start is not None:
        dtl_start = dtl_start.timestamp()
    
    if dtl_end is not None:
        dtl_end = dtl_end.timestamp()

    q = queue.Queue(25)

    th = threading.Thread(
        target=read_worker,
        daemon=True
    )
    th.start()

    while True:
        blob = q.get()
        if blob is None:
            break
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


def build_mask():
    """Writes out a spectral mask in the form of coeffients multiplied with each channel.

    The baseband output from the mixer is distorted and attenuated. This tries to estimate
    the attenuation/response and then calculates a sequence of coefficients to equalize the
    frequency response. This way channels can be compared with each other in terms of 
    magnitude.
    """
    s = None
    sc = 0
    st = time.time()
    for _, c, _ in enumerate_channel():
        #plt.plot(c)
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
    with open('spectral-mask.pickle', 'rb') as fd:
        return pickle.load(fd)


def all_time_spectrum_plot():
    px = []
    py = []

    mask = load_mask()
    for ts, c, f in enumerate_channel():
        c *= mask
        for x in range(len(c)):
            px.append(f[x])
            py.append(c[x])

    plt.title('Spectrum Plot')
    plt.xlabel('frequency')
    plt.ylabel('magnitude')
    plt.scatter(px, py, s=0.1)
    plt.show()


def running_mean_plot():
    mask = load_mask()
    ts_least = None
    ts_most = None
    f_least = None
    f_most = None

    print('Scanning data for bounds...')
    for ts, c, f in enumerate_channel():
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
    freq_bins = 4096
    time_period = 60 * 60
    time_period_high_index = int((ts_most - ts_least) / time_period)
    time_period_count = time_period_high_index + 1
    period_resolution = min(time_period_count, 4096)

    m3d = np.zeros((time_period_count, freq_bins, 2), np.float64)
    
    print('Accumulating energy...')
    for ts, c, cf in enumerate_channel():
        c *= mask
        ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))
        for x in range(len(c)):
            f = cf[x]
            m = c[x]
            f_pos = round((f - f_least) / f_delta * (freq_bins - 1))
            m3d[ts_pos, f_pos, 0] += m
            m3d[ts_pos, f_pos, 1] += 1.0
    
    m3d = m3d[:, :, 0] / m3d[:, :, 1]

    plt.imshow(m3d)
    plt.show()


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

    for ts, c, f in enumerate_channel('scanning data for bounds...', args_start, args_end):
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

    for ts, c, cf in enumerate_channel('calculating mean energy per channel...', args_start, args_end):
        #ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))
        c *= mask
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        f_pos = f_pos.astype(np.uint32)
        mpc[f_pos, 0] += c
        mpc[f_pos, 1] += 1.0

    mpc = mpc[:, 0] / mpc[:, 1]

    # sum per channel
    spc = np.zeros((freq_bins, 2), np.float64)

    for ts, c, cf in enumerate_channel('calculating standard deviation per channel...', args_start, args_end):
        #ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))
        c *= mask
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        f_pos = f_pos.astype(np.uint32)
        spc[f_pos, 0] += (c - mpc[f_pos]) ** 2
        spc[f_pos, 1] += 1.0

        #for x in range(len(c)):
        #    f = cf[x]
        #    m = c[x]
        #    
        #    spc[f_pos, 0] += (m - mpc[f_pos]) ** 2
        #    spc[f_pos, 1] += 1.0

    # std deviation per channel
    stdpc = np.sqrt(spc[:, 0] / spc[:, 1])

    sigma = np.zeros((freq_bins, period_resolution), np.float64)
    m_energy = np.zeros((freq_bins, period_resolution), np.float64)

    for ts, c, cf in enumerate_channel('calculating sigma per channel...', args_start, args_end):
        c *= mask

        ts_pos = np.round((ts - ts_least) / ts_delta * (period_resolution - 1))
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        ts_pos = ts_pos.astype(np.uint32)
        f_pos = f_pos.astype(np.uint32)
        
        #a = np.abs((c - mpc[f_pos]) / stdpc[f_pos])
        
        a = (c - mpc[f_pos]) / stdpc[f_pos]

        try:
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
        build_mask()

    if args.build:
        sigma_plot(args)

    with open(args.sigma_pickle, 'rb') as fd:
        sigma = pickle.load(fd)

    with open(args.energy_pickle, 'rb') as fd:
        m_energy = pickle.load(fd)

    with open('times.pickle', 'rb') as fd:
        time_period_marks = pickle.load(fd)

    #time_period_marks = mdates.date2nums(time_period_marks)

    fig, ax = plt.subplots()

    plt.title('Energy')
    ax.set_ylabel('Frequency')
    ax.set_xlabel('Time')
    ax.xaxis_date()
    ax.imshow(m_energy, aspect='auto', extent=[0, 1, 6e9, 70e6], cmap='rainbow')
    plt.show()

    sigma = signal.correlate2d(sigma, [[0, 1, 0], [0, 1, 0]], mode='same')

    plt.title('Sigma')
    plt.ylabel('Frequency')
    plt.xlabel('Time')
    plt.imshow(sigma, extent=[70e6, 6e9, 6e9, 70e6], aspect='auto')
    plt.show()


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
    ap.add_argument('--time-period-max-res', type=int, default=4096)
    ap.add_argument('--sigma-pickle', type=str, default='sigma.pickle')
    ap.add_argument('--energy-pickle', type=str, default='m_energy.pickle')
    ap.add_argument('--build', default=True, action=argparse.BooleanOptionalAction)
    main(ap.parse_args())
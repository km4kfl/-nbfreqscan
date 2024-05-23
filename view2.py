import numpy as np
import pickle
import time
import matplotlib.pyplot as plt
import matplotlib.colors as cmap
import datetime as dt
import scipy.ndimage as ndimage
import scipy.signal as signal
import os

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


def enumerate_channel():
    dtl = dt.datetime(2024, 5, 18, 14, 23, 0)
    dtl = dtl.timestamp()
    z = 0
    with open('s3radio248.pickle', 'rb') as fd:
        fd.seek(2781259173)
        try:
            while True:
                key, blob = pickle.load(fd)
                #print(key[1], dtl, fd.tell())
                if key[1] < dtl:
                    continue                
                for sample in blob:
                    src_ndx = sample['src_ndx']
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
                z += 1
                #if z > 20:
                #    break
        except EOFError:
            pass

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
        print(c)
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
    
#build_mask()

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

def sigma_plot():
    mask = load_mask()
    ts_least = None
    ts_most = None
    f_least = None
    f_most = None

    print('Scanning data...')
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
    time_period = 60 * 5
    time_period_high_index = int((ts_most - ts_least) / time_period)
    time_period_count = time_period_high_index + 1
    period_resolution = min(time_period_count, 4096)
    freq_bins = period_resolution

    # mean per channel
    mpc = np.zeros((freq_bins, 2), np.float64)

    print('Calculating mean energy per channel...')
    for ts, c, cf in enumerate_channel():
        #ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))

        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        f_pos = f_pos.astype(np.uint32)
        mpc[f_pos, 0] += c
        mpc[f_pos, 1] += 1.0

        #for x in range(len(c)):
        #    f = cf[x]
        #    m = c[x]
        #    f_pos = round((f - f_least) / f_delta * (freq_bins - 1))
        #    mpc[f_pos, 0] += m
        #    mpc[f_pos, 1] += 1.0

    # sqrt((e - mean(e)) ** 2)

    mpc = mpc[:, 0] / mpc[:, 1]

    # sum per channel
    spc = np.zeros((freq_bins, 2), np.float64)
    
    print('Calculating standard deviation per channel...')

    for ts, c, cf in enumerate_channel():
        #ts_pos = round((ts - ts_least) / ts_delta * (period_resolution - 1))

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

    print('Calculating sigma per channel...')

    sigma = np.zeros((freq_bins, period_resolution), np.float64)
    m_energy = np.zeros((freq_bins, period_resolution), np.float64)

    for ts, c, cf in enumerate_channel():
        ts_pos = np.round((ts - ts_least) / ts_delta * (period_resolution - 1))
        f_pos = np.round((cf - f_least) / f_delta * (freq_bins - 1))
        ts_pos = ts_pos.astype(np.uint32)
        f_pos = f_pos.astype(np.uint32)
        a = np.abs((c - mpc[f_pos]) / stdpc[f_pos])
        sigma[f_pos, ts_pos] = np.max(
            [a, sigma[f_pos, ts_pos]],
            axis=0
        )

        m_energy[f_pos, ts_pos] = np.max(
            [c, m_energy[f_pos, ts_pos]],
            axis=0
        )

        #for x in range(len(c)):
        #    f = cf[x]
        #    m = c[x]
        #    f_pos = round((f - f_least) / f_delta * (freq_bins - 1))
        #    sigma[f_pos, ts_pos] = max(
        #        (m - mpc[f_pos]) / stdpc[f_pos],
        #        sigma[f_pos, ts_pos]
        #    )

    with open('sigma.pickle', 'wb') as fd:
        pickle.dump(sigma, fd)

    with open('m_energy.pickle', 'wb') as fd:
        pickle.dump(m_energy, fd)

    #plt.ylabel('frequency')
    #plt.xlabel('time')
    #plt.imshow(sigma, extents=[1, 2, 3, 4])
    #plt.show()

    #plt.imshow(m3d)
    #plt.show()

sigma_plot()

with open('sigma.pickle', 'rb') as fd:
    sigma = pickle.load(fd)

with open('m_energy.pickle', 'rb') as fd:
    m_energy = pickle.load(fd)

pattern = np.array([
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 1, 0],
])

print(sigma.shape, pattern.shape)

#sigma = signal.correlate2d(sigma, pattern, mode='full')

#sigma[sigma < 6] = 0.0
#sigma[sigma > 6] = 1.0

#sigma = ndimage.gaussian_filter(sigma, 2.0)

plt.imshow(m_energy)
plt.show()

plt.ylabel('frequency')
plt.xlabel('time')
plt.imshow(sigma, extent=[0, 6e9, 6e9, 70e6])
plt.show()

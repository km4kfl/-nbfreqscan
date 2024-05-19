import numpy as np
import pickle
import time
import matplotlib.pyplot as plt
import datetime as dt

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
    with open('s3radio248.pickle', 'rb') as fd:
        fd.seek(2781259173)
        try:
            while True:
                key, blob = pickle.load(fd)
                print(key[1], dtl, fd.tell())
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
                            points[ndx] = item['b0']
                            freqs[ndx] = item['freq'] + freq
                        yield points, freqs
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
    for c, _ in enumerate_channel():
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

px = []
py = []

mask = load_mask()
for c, f in enumerate_channel():
    c *= mask
    for x in range(len(c)):
        px.append(f[x])
        py.append(c[x])

plt.title('Spectrum Plot')
plt.xlabel('frequency')
plt.ylabel('magnitude')
plt.scatter(px, py, s=0.1)
plt.show()
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import pickle
import math
import time
from scipy import ndimage

a = {}
b = {}
c = {}

with open('plot', 'rb') as fd:
    while True:
        try:
            mt, freq, b0, b1, board_ndx = pickle.load(fd)
        except EOFError:
            break
        board_ndx = str(board_ndx)
        if board_ndx + '.0' not in a:
            a[board_ndx + '.0'] = []
            b[board_ndx + '.0'] = []
            a[board_ndx + '.1'] = []
            b[board_ndx + '.1'] = []
            c[board_ndx + '.0'] = []
            c[board_ndx + '.1'] = []     
        a[board_ndx + '.0'].append(freq)
        b[board_ndx + '.0'].append(b0)
        a[board_ndx + '.1'].append(freq)
        b[board_ndx + '.1'].append(b1)
        c[board_ndx + '.0'].append(mt)
        c[board_ndx + '.1'].append(mt)

print('data loaded')

print('sample count', len(a['0.0']))

def time_of_day_analysis(
    start_time,
    time_period,
    bins,
    ts,
    freq,
    mag):
    def process_ldata(ldata):
        ldata = np.array(ldata)
        # ts, freq, mag
        w = ldata[:, 2] - np.mean(ldata[:, 2])
        mags, edges = np.histogram(
            ldata[:, 1], weights=w,
            bins=bins
        )
        return mags

    out = []
    cur_key = None
    ldata = []
    for x in range(len(ts)):
        #print(dt.datetime.fromtimestamp(ts[x]))

        tse = math.floor((ts[x] - start_time) / time_period)

        #print('tse', tse, ts[x] - start_time)

        while len(out) < tse + 1:
            out.append(None)

        #if cur_key is not tse.day:
        if cur_key != tse:
            if len(ldata) > 0:
                print('processing', tse)
                out[tse] = process_ldata(ldata)
            #cur_key = tse.day
            cur_key = tse
            ldata = []
        ldata.append((ts[x], freq[x], mag[x]))

    while len(out) < tse + 1:
        out.append(None)

    if len(ldata) > 0:
        print('processing', tse)
        out[tse] = process_ldata(ldata)
        out_sz = len(out[tse])
        out_dtype = out[tse].dtype

    print('padding with zeros', len(out))
    for x in range(len(out)):
        if out[x] is None:
            # use nans so we can ignore them in further
            # calculations
            out[x] = np.zeros(out_sz, out_dtype)
            out[x] /= 0

    out = np.array(out)

    #sigma = (out - np.mean(out, axis=0)) / np.std(out, axis=0)

    out2 = np.zeros(out.shape, out.dtype)

    print('doing streaming sigma')
    sst = time.time()
    for y in range(out.shape[1]):
        if time.time() - sst > 5:
            sst = time.time()
            print('progress', y / (out.shape[1] - 1))
        for x in range(1, out.shape[0]):
            chunk = out[0:x, y]
            std = np.nanstd(chunk)
            if std == 0.0 or np.isnan(std):
                continue
            chunk2 = (chunk - np.nanmean(chunk)) / std
            point = chunk2[-1]
            out2[x, y] = point

    #sigma = ndimage.gaussian_filter(sigma, 2.0)

    return out2

'''
f = []

for k in c:
    _c = c[k]
    _a = a[k]
    _b = b[k]
    for x in range(len(_c)):
        f.append((_c[x], _a[x], _b[x]))

f.sort(key=lambda item: item[0])

f = np.array(f)
time_of_day_analysis(f[:, 0], f[:, 1], f[:, 2])
'''

bins = 128
time_period_hours = 0.5
time_period = int(60 * 60 * time_period_hours)

# earliest start time
est = time.time()

for k in c:
    est = min(c[k][0], est)


sigma_l = []
sigma = None
sigma_c = 0.0
rows = 0
for k in c:
    print('time of day analysis', k)
    s = time_of_day_analysis(est, time_period, bins, c[k], a[k], b[k])
    sigma_l.append(s)
    if s.shape[0] > rows:
        rows = s.shape[0]
    
nsigma_l = []

for s in sigma_l:
    ns = np.zeros((rows, s.shape[1]), s.dtype)
    ns /= 0.0
    ns[0:s.shape[0], :] = s
    nsigma_l.append(ns)

sigma = np.nanmean(nsigma_l, axis=0)

tpl = (np.min(sigma), np.max(sigma))

if tpl[0] < 6 or tpl[1] > 6:
    vmin = tpl[0]
    vmax = tpl[1]
else:
    vmin = -6
    vmax = 6

plt.title('%.2f Hour Sigma Analysis [%.2f, %.2f]' % (
    time_period_hours,
    tpl[0], tpl[1]
))

plt.imshow(sigma, extent=[
    70e6, 6e9, 6e9, 70e6
], vmin=vmin, vmax=vmax)
#plt.savefig('sigma-analysis.png')
plt.show()
exit()

plt.title('Response at Time')
plt.xlabel('Time')
plt.ylabel('Mean Magnitude')
for data_name in a:
    #a_dt = [dt.datetime.fromtimestamp(v) for v in a[data_name]]
    plt.plot(b[data_name], label=data_name)
plt.legend()
plt.show()
plt.title('Response At Frequency')
plt.xlabel('Frequency')
plt.ylabel('Mean Magnitude')
for data_name in a:
    plt.scatter(a[data_name], b[data_name], label=data_name, s=0.1)
plt.legend()
plt.show()

'''
# This reads the lbtest.py data and plots it.
a = []
b = []

with open('temp.data', 'rb') as fd:
    a = pickle.load(fd)
    b = pickle.load(fd)

plt.title('Correlation')
plt.xlabel('Sample/Time')
plt.ylabel('Magnitude/Response')
plt.plot(b, label='Antenna')
plt.plot(a, label='Cable')
plt.legend()
plt.show()
'''
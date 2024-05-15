import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import pickle
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

def time_of_day_analysis(ts, freq, mag):
    def process_ldata(ldata):
        ldata = np.array(ldata)
        mags, edges = np.histogram(
            ldata[:, 1], weights=ldata[:, 2],
            bins=256
        )
        return mags

    out = []
    cur_key = None
    ldata = []
    for x in range(len(ts)):
        tse = dt.datetime.fromtimestamp(ts[x])
        #if cur_key is not tse.day:
        if cur_key is not tse.hour:
            if len(ldata) > 0:
                print('processing', tse)
                out.append(process_ldata(ldata))
            #cur_key = tse.day
            cur_key = tse.hour
            ldata = []
        ldata.append((ts[x], freq[x], mag[x]))

    if len(ldata) > 0:
        print('processing', tse)
        out.append(process_ldata(ldata))

    out = np.array(out)

    sigma = (out - np.mean(out, axis=0)) / np.std(out, axis=0)

    #sigma = ndimage.gaussian_filter(sigma, 2.0)

    plt.title('Hourly Sigma Analysis')   
    plt.imshow(sigma, extent=[
        70e6, 6e9, 6e9, 70e6
    ])
    plt.show()

time_of_day_analysis(c['2.1'], a['2.1'], b['2.1'])
exit()

plt.title('Response at Time')
plt.xlabel('Time')
plt.ylabel('Mean Magnitude')
for data_name in a:
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
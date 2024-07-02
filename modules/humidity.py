import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as signal

def entry(params):
    time_period_marks = params['time_period_marks']
    sigma = params['sigma']
    args = params['args']

    # humidity level plotting
    fig, ax = plt.subplots()
    q = sigma[4630:5900, :]
    #q = sigma[:, :]
    q = np.mean(q, axis=0)
    ax.set_xlabel('Time')
    ax.set_ylabel('Average Sigma Over Frequency Channels')
    ax.xaxis_date()
    ax.plot(time_period_marks, q)
    plt.show()

    beta = 100
    qq = np.ones(beta) / beta
    qd = signal.convolve(q, qq, mode='same')
    q = signal.convolve(q, qq, mode='valid')

    fig, ax = plt.subplots()
    h = int((len(time_period_marks) - len(q)) // 2)
    ax.set_xlabel('time')
    ax.set_ylabel('Magnitude')
    ax.plot(time_period_marks, qd)
    ax.xaxis_date()
    plt.show()

    r = []
    for x in range(sigma.shape[0]):
        r.append(np.max(signal.correlate(sigma[x, :], q, mode='valid')))

    fig, ax = plt.subplots()
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Correlation')
    r = signal.convolve(r, qq, mode='valid')
    #ax.plot(np.linspace(70e6, 6e9, len(r)), r)
    ax.plot(r)
    plt.show()

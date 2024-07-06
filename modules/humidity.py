import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as signal

def entry(params):
    time_period_marks = params['time_period_marks']
    sigma = params['sigma']
    args = params['args']

    fig, ax = plt.subplots()

    # For my antenna this is the most sensitive frequency range and it 
    # just so happens to not have much man-made interference in it.
    q = sigma[4630:5900, :]
    
    # Increase the SNR by averaging over the frequencies.
    q = np.mean(q, axis=0)
    ax.set_xlabel('Time')
    ax.set_ylabel('Average Sigma Over Frequency Channels')
    ax.xaxis_date()
    ax.plot(time_period_marks, q)
    plt.show()

    # Increase the precision by averaging over time.
    beta = 30
    qq = np.ones(beta) / beta
    qd = signal.convolve(q, qq, mode='same')
    q = signal.convolve(q, qq, mode='valid')

    fig, ax = plt.subplots()
    h = int((len(time_period_marks) - len(q)) // 2)

    # Show the average.
    ax.set_xlabel('Time')
    ax.set_ylabel('Magnitude')
    ax.plot(time_period_marks, qd)
    ax.xaxis_date()
    plt.show()

    # Do an interesting correlation over all frequencies/bins.
    r = []
    for x in range(sigma.shape[0]):
        r.append(np.max(signal.correlate(sigma[x, :], q, mode='valid')))

    fig, ax = plt.subplots()
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Correlation')
    r = signal.convolve(r, qq, mode='valid')
    ax.plot(np.linspace(70e6, 6e9, len(r)), r)
    #ax.plot(r)
    plt.show()

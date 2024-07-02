import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as signal

def entry(params):
    time_period_marks = params['time_period_marks']
    sigma = params['sigma']
    m_energy = params['m_energy']
    args = params['args']

    fig, ax = plt.subplots()

    plt.title('Energy')
    ax.set_ylabel('Frequency')
    ax.set_xlabel('Time')
    ax.xaxis_date()
    ax.imshow(m_energy ** args.log, aspect='auto', extent=[time_period_marks[0], time_period_marks[-1], 6e9, 70e6])
    plt.show()
    plt.close()
    '''
    '''
    fig, ax = plt.subplots()

    if args.pat_x > 1 or args.pat_y > 1:
        pat = np.ones(args.pat_x, sigma.dtype)
        pat = np.tile(pat, args.pat_y).reshape((args.pat_y, args.pat_x))
        sigma = signal.correlate2d(sigma, pat, mode='same')

    plt.title('Sigma')
    ax.set_ylabel('Frequency')
    ax.set_xlabel('Time')
    ax.xaxis_date()
    ax.imshow(
        sigma ** args.log,
        extent=[time_period_marks[0], time_period_marks[-1], 6e9, 70e6],
        aspect='auto'
    )
    plt.show()

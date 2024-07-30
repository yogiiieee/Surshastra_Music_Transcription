fs = 44100 # sampling frequency
nfft = 2048 # length of fft window
overlap = 0.5 # Hop overlap percentage
hop_length = int(nfft*(1-overlap)) # number of samplws between successive frames
n_bins = 72 # number of frequency bins
mag_exp = 4 # magnitude exponent
pre_post_max = 6 # pre- and post- samples for peak picking
cqt_threshold = -61 # threshold for CQT dB levels. all values below threshold are set to -120 dB
# NB Frequency Scanner
This is a simple tool used to scan a range of frequencies using a Nuand BladeRF card. It requires that the BladeRF library has been compiled. The library can be found at `https://github.com/Nuand/bladeRF`.

The scanner is in three parts. The first is a server program, `freqscanserver.py`, which is run for each bladeRF board. Next a configuration file is created using the format shown below. Finally, the client program, `freqscanclient.py`, is executed which will use the configuration file to connect to each avaliable server process and fetch then write the data.

The configuration file is used by both the server to know which port it should listen on and by the client to know what system to connect to.

# Command Line Parameters

## Server (freqscanserver.py)

The samples per second (`--sps`) can now be specified at the command line. If one wants to channelize
the baseband then the argument `--channel-bw` can be used. Be aware that unless `--bw` is specified it
will default to 200e3-hertz which would be unexpected in many cases.

## Client (freqscanclient.py)

The client takes `--config` and `--output`. The `--output` is a simple Python pickle based output file
for the data.

## S3 Client (s3shuffle.py)

This extends `freqscanclient.py` within the code by using an Amazon S3 bucket to store the output
and an adapter called `view_fetch.py` is included to pull this data and recreate the local file
if desired. Instead of running `freqscanclient.py` one runs `s3shuffle.py` in it's place.

### Dependencies

You need to execute `python3 -m pip install boto3` to get the Amazon client library ready.

# Example Configuration
```
servers:
  9da:
    enabled: true
    host: 192.168.0.105
    port: 10000
    freq-min: 70e6
    freq-max: 6e9
  5bb:
    enabled: true
    host: 192.168.0.105
    port: 10001
    freq-min: 70e6
    freq-max: 6e9    
  8bb:
    enabled: true
    host: 192.168.0.100
    port: 10002
    freq-min: 70e6
    freq-max: 6e9    
  e85:
    enabled: true
    host: 192.168.0.100
    port: 10003
    freq-min: 70e6
    freq-max: 6e9
```

The `9da`, `5bb`, `8bb`, and `e85` are the first three digits of the serial numbers for the four BladeRF cards used in the example configuration. The host and port are used by the server to bind a network socket and are used by the client to connect. 

You can use whatever number of digits/letters the BladeRF library supports for specifying cards. This is used with `libusb:serial=<digits/letters>` when opening the device. You can use `bladeRF-cli -p` to probe for the card's serials and `bladeRF-cli -d libusb:serial=<serial>` to test the serial. If it works with `bladeRF-cli` then it will work in the config file.

You can use the host address `0.0.0.0` but then the client won't know what address to connect with
unless you use a seperate configuration file for the client.

# Downloading from S3

To download the channelized data from S3 use the `s3fetch.py`. You might call it, for example,
like this: `python Z:\nbfreqscan\s3fetch.py --cred-path Z:\nbfreqscan\s3sak.txt --bucket-name radio248 --data-path .\s3radio248.pickle`.

The `--cred-path` is a text file with two lines. The first line is the Amazon S3 `access key` and the second line is the `secret access key`. You can get these from your Amazon AWS account.

The `--bucket-name` is exactly what it says. This is the name of the Amazon S3 bucket.

The `--data-path` can be a new file or an existing file. If it is an existing file it will scan it and determine what you have already downloaded, skip what was already downloaded, and append any new data. I use it like this to collect new data.

_If you didn't use `s3shuffle.py` then the data is saved locally and you can use the data like it is or skip this section because you don't need to download from S3.

# Viewing Data

I've included my own program for viewing the data. I've created a modules system for it so you can easily extend it for your own needs. I've included two examples: `humidity` and `energysigma`. The humidity module is some testing I was doing on measuring humidity levels and energysigma is a general case that shown work for almost any dataset.

_You will want to include the option `--build-mask` if it is the first time running it. This will try to build a spectral mask using averages. It works well when scanning over a large swath of frequencies that are mostly noise._

The spectral mask is used to compensate for the non-linear responsivity of the mixer output. It happens because the bandband is warped in magnitude such that frequencies near DC are attenuated more or less than frequencies near the edges.

For example, `python Z:\nbfreqscan\view_local_store.py --build --time-period-max-res 2048 --freq-res 16000 --log 1.0 --pat-y 100 --pat-x 1 --time-period 300 --start "6/28/24 00:00:00" --module energysigma`.

_I forgot to mention above to use the --data argument to specify the local data file that is created by the `s3fetch.py` program._

The above uses a logarithmic scale of 1.0 (no log scale) for the sigma plot, has a start date and time, uses the module energysigma, uses a pattern convolution of 100 tall and 1 wide (averaging), has a time period of 300 seconds, the time period maximum bin count is 2048 and the frequency maximum bin count is 16000. 

You can also use `--no-build` to use the cached results where it only runs the module and doesn't build the data. Using `--no-build` ignores most of the parameters as these were used when building the intermediate data (stored in some local files).

If you omit `--start` and `--end` it will build with ALL of the data which may be intended and is quite useful sometimes.

# Performance

You might notice it runs slow. The reason is I'm dealing with a very large dataset that won't fit into RAM nor will it fit using virtual memory. Because of this I have to stream the data in and that causes it to run magnitudes slower. I also stream the data in multiple times which if you are using the whole dataset means it reads the whole data file multiple times - as you can figure for gigabytes of data this can take some time.

There is a faster version for datasets that fit into memory and a much simpler program. I used to have it written but it evolved into what it is now. The process is simple if you need to recreate it just copy what I've done and turn everything into Numpy operations. You can pretty much do it all in almost
one line of code.

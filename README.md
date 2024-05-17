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

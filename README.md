# NB Frequency Scanner
This is a simple tool used to scan a range of frequencies using a Nuand BladeRF card. It requires that the BladeRF library has been compiled. The library can be found at `https://github.com/Nuand/bladeRF`.

The scanner is in three parts. The first is a server program, `freqscanserver.py`, which is run for each bladeRF board. Next a configuration file is created using the format shown below. Finally, the client program, `freqscanclient.py`, is executed which will use the configuration file to connect to each avaliable server process and fetch then write the data.

The configuration file is used by both the server to know which port it should listen on and by the client to know what system to connect to.

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

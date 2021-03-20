# Asyncio Proxy Server Herd

A server herd network structure built using Python's asyncio library.

Clients can send commands to save their location data and query the Google Places API. When multiple server instances are running, the data is propagated between servers via a flooding algorithm.

See [my research pdf](ServerHerdResearch.pdf) for more information on the functionality of the server herd and on asyncio.

## Quick Start
- Download server.py and create a new "config.py" in the same directory
- In config.py:
```
API_KEY = <Your Google Places Developer API Key>
```
- Open a server using a shell (you must specify a server name)
```
python3 server.py <server name>
```
- Send requests to the server(s)
```
python3 server.py Riley
telnet 127.0.0.1 8000
IAMAT myClient +34.068930-118.445127 1614209128.918963997
WHATSAT myClient 10 5
<...>
```
### Notes
- To support multiple servers in the herd, start other servers in other shell sessions
- Only one server needs to be running at minimum to serve requests

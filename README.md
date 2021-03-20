# asyncio-server-herd
A server herd network structure built using Python's asyncio library.

Clients can send commands to save their location data and query the Google Places API. When multiple server instances are running, the data is propagated between servers via a flooding algorithm.

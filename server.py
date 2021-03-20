from config import API_KEY
import asyncio
import argparse
import time
import sys
import aiohttp
import json



# Port assignments can be customized here
ports = {
    "Riley": 8000,
    "Steve": 8001,
    "Alex": 8002,
    "Wheatley": 8003,
    "Barney": 8004
}

# Server adjacency can be customized here
# These relationships dictate the behavior of the flooding algorithm
adjacent_servers = {
    "Riley": ["Steve", "Alex"],
    "Steve": ["Riley", "Barney"],
    "Alex": ["Wheatley", "Riley", "Barney"],
    "Wheatley": ["Alex", "Barney"],
    "Barney": ["Steve", "Alex", "Wheatley"]
}

localhost = "127.0.0.1"


class Server:
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port
        self.client_recent = {}

    async def handle_request(self, reader, writer):
        raw_data = await reader.read(100000000)
        decoded_message = raw_data.decode()
        server_time_received = time.time()
        log.write(f"RECEIVED: {decoded_message}\n")

        # determine message validity and type
        token_list = decoded_message.strip().split()
        command_type = self.identify_command(token_list)

        if command_type == "IAMAT":
            server_response = await self.handle_IAMAT(token_list, str(server_time_received))
        elif command_type == "WHATSAT":
            server_response = await self.handle_WHATSAT(token_list)
        elif command_type == "AT":
            await self.handle_AT(token_list, decoded_message)
        else:
            server_response = "? " + decoded_message + "\n"

        if command_type != "AT":
            log.write(f"SENT: {server_response}\n")
            log.flush()
            writer.write(server_response.encode())
            await writer.drain()
        writer.close()


    def identify_command(self, token_list):
        if token_list[0] == "IAMAT" and self.is_valid_IAMAT(token_list):
            return "IAMAT"
        elif token_list[0] == "WHATSAT" and self.is_valid_WHATSAT(token_list):
            return "WHATSAT"
        elif token_list[0] == "AT" and self.is_valid_AT(token_list):
            return "AT"
        else:
            return "?"
             

    # return tuple (bool, tuple)
    # example for valid coords: (True, (+34.53, -23.42))
    # example for invalid coords: (False, (0, 0))
    def parse_coords(self, coords):
        if coords[0] not in ["+", "-"] or len(coords) < 4 or coords[-1] in ["+", "-"]:
            return (False, (0, 0))
        # count number of symbols
        plus_count = coords.count("+")
        neg_count = coords.count("-")
        total = plus_count + neg_count
        if total != 2:
            return (False, (0, 0))
        # start parsing from the first index to avoid the first sign char
        for i in range(1, len(coords)):
            if coords[i] in ["+", "-"]:
                lat = coords[:i]
                long = coords[i:]
                if is_number(lat[1:]) and is_number(long[1:]):
                    return (True, (lat, long))
                else:
                    return (False, (0, 0))
        return (False, (0, 0))

    def is_valid_IAMAT(self, token_list):
        coords = token_list[2]
        client_timestamp = token_list[3]
        if self.parse_coords(coords)[0] and is_number(client_timestamp):
            return True
        return False
    
    def is_valid_WHATSAT(self, token_list):
        client = token_list[1]
        radius = token_list[2]
        bound = token_list[3]
        if client in self.client_recent and is_number(radius) and is_number(bound) and 0 < float(radius) <= 50 and 0 < int(bound) <= 20:
            return True
        return False
    
    def is_valid_AT(self, token_list):
        server = token_list[1]
        time_diff = token_list[2]
        coords = token_list[4]
        client_timestamp = token_list[5]
        if server in ports and time_diff[0] in ["+", "-"] and is_number(time_diff[1:]) and self.parse_coords(coords)[0] and is_number(client_timestamp):
            return True
        return False

    async def flood_adjacents(self, message):
        for adjacent in adjacent_servers[self.name]:
            try:
                reader, writer = await asyncio.open_connection(localhost, ports[adjacent])
                log.write(f"Connected to {adjacent}\n")
                log.write(f"SENT TO {adjacent}: {message}\n")
                log.flush()
                writer.write(message.encode())
                await writer.drain()
                log.write(f"Disconnecting from {adjacent}\n")
                writer.close()
                await writer.wait_closed()
            except:
                log.write(f"Exception occurred when connecting to {adjacent}\n")
                log.flush()
    
    async def handle_IAMAT(self, token_list, server_time_received):
        client = token_list[1]
        coords = token_list[2]
        client_timestamp = token_list[3]

        time_diff = str(float(server_time_received) - float(client_timestamp))
        if time_diff[0] != "-":
            time_diff = "+" + time_diff
        self.client_recent[client] = [coords, time_diff, self.name, client_timestamp]

        AT_message = f"AT {self.name} {time_diff} {client} {coords} {client_timestamp}\n"

        await self.flood_adjacents(AT_message)

        return AT_message
    
    async def handle_WHATSAT(self, token_list):
        client = token_list[1]
        radius_in_meters = str(float(token_list[2]) * 1000)
        bound = int(token_list[3])
        coords, time_diff, og_server, client_timestamp = self.client_recent[client]
        lat, long = self.parse_coords(coords)[1]
        lat.replace("+", "")
        long.replace("+", "")
        places_ret = await self.query_google_places(lat, long, radius_in_meters, bound)
        AT_message = f"AT {og_server} {time_diff} {client} {coords} {client_timestamp}\n"
        return AT_message + places_ret + "\n\n"

    async def handle_AT(self, token_list, decoded_message):
        og_server = token_list[1]
        time_diff = token_list[2]
        client = token_list[3]
        coords = token_list[4]
        client_timestamp = token_list[5]
        if client in self.client_recent:
            if float(client_timestamp) > float(self.client_recent[client][3]):
                log.write("Updating client information\n")
                log.flush()
                self.client_recent[client] = [coords, time_diff, og_server, client_timestamp]
                await self.flood_adjacents(decoded_message)
            else:
                log.write("Client information already up-to-date\n")
                log.flush()
        else:
            log.write("Updating client information for new client\n")
            log.flush()
            self.client_recent[client] = [coords, time_diff, og_server, client_timestamp]
            await self.flood_adjacents(decoded_message)

    async def query_google_places(self, lat, long, radius_in_meters, bound):
        async with aiohttp.ClientSession() as session:
            places_url=f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{long}&radius={radius_in_meters}&key={API_KEY}"
            async with session.get(places_url) as response:
                result = await response.text()
            result_object = json.loads(result)
            if len(result_object["results"]) <= bound:
                return result
            else:
                result_object["results"] = result_object["results"][:bound]
                ret = json.dumps(result_object, indent=4).rstrip("\n")
                return ret

    async def run_forever(self):
        log.write(f"{self.name} server starting up\n")
        log.flush()
        # start up server
        server = await asyncio.start_server(self.handle_request, self.ip, self.port)

        # Serve requests until Ctrl+C is pressed
        async with server:
            await server.serve_forever()
        
        log.write(f"{self.name} server shutting down\n")
        log.flush()
        # Close the server
        server.close()


def is_number(num):
    try:
        float(num)
        return True
    except:
        return False



if __name__ == "__main__":
    parser = argparse.ArgumentParser('Argument Parser')
    parser.add_argument('server_name', type=str, help='required server name input')
    args = parser.parse_args()
    if args.server_name not in ports:
        print("Invalid server name received. Exiting.")
        sys.exit()
    server = Server(args.server_name, localhost, ports[args.server_name])
    
    global log
    log_name = args.server_name + "-server-log.txt"
    log = open(log_name, "w")
    try:
        asyncio.run(server.run_forever())
    except KeyboardInterrupt:
        log.close()

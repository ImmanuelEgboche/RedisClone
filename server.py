from gevent.pool import Pool
from gevent.server import StreamServer
from protocolHandler import ProtocolHandler, CommandError, Error, Disconnect

class Server(object):
    def __init__(self, host='127.0.0.1', port=31337, max_clients=64):
        self._pool = Pool(max_clients)
        self._server = StreamServer(
            (host,port),
            self.connection_handler,
            spawn=self._pool)
        
        self._protocol = ProtocolHandler()
        self._kv = {}

        self._commands = self.get_commands()

    def get_commands(self):
        return{
            'GET': self.get,
            'SET': self.set,
            'DELETE': self.delete,
            'FLUSH': self.flush,
            'MGET': self.mget,
            'MSET': self.mset
        }
    
    def get(self, key):
        value = self._kv.get(key)
        return value if value is not None else None

    def set(self, key, value):
        self._kv[key] = value
        return 1 
    
    def delete(self, key):
        if key in self._kv:
            del self._kv[key]
            return 1
        return 0
    
    def flush(self):
        kvlen = len(self._kv)
        self._kv.clear()
        return kvlen
    
    def mget(self, *keys):
        return [self._kv.get(key) for key in keys]
    
    def mset(self,*items):
        data = list(zip(items[::2], items[1::2]))
        for key, value in data:
            self._kv[key] = value
        return len(data)

    def connection_handler(self,conn, address):
        print(f"new connection from {address}")
        # Convert "conn" (a socket object) into a file-like object
        socket_file = conn.makefile('rwb')

        # Process client requests until client disconnects
        while True:
            try:
                data = self._protocol.handle_request(socket_file)
                print(f"Server received data: {data}")
            except Disconnect:
                print("Client Disconnected")
                break
            except Exception as e: 
                print(f"Error handling request: {str(e)}")
                break

            try:
                resp = self.get_response(data)
                print(f"Server sending response: {resp}")
            except CommandError as exc:
                resp = Error(exc.args[0])
                print(f"Command Error: {resp}")    

            self._protocol.write_response(socket_file, resp)

    def get_response(self, data):
        #Here the unpacking of the data from the client will begin and the execution of what they ask will be done
        if not isinstance(data, list):
            try:
                data = data.split()
            except:
                raise CommandError('Request my be list or simple string')
    
        if not data:
            raise CommandError('Missing command')
        
        command = data[0].upper()
        if command not in self._commands:
            raise CommandError('Unrecognised command: %s' % command)
        
        return self._commands[command](*data[1:])
            
    def run(self):
        self._server.serve_forever()
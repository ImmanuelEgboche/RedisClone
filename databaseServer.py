from gevent import socket 
from gevent.pool import Pool
from gevent.server import StreamServer

from collections import namedtuple
from io import BytesIO
from socket import error as socket_error

# Exceptions will be used to notify connection-handling loops of problems
class CommandError(Exception): 
    """Raised when an invalid command is recieved."""
    pass

class Disconnect(Exception): 
    """Raised when an invalid command is recieved."""
    pass

# Named tuple for error reponses
Error = namedtuple('Error', ('message',))

class ProtocolHandler(object):
    def __init__(self):
        self.handlers = {
            b'+': self.handle_simple_string,
            b'-': self.handle_error,
            b':': self.handle_integer,
            b'$': self.handle_string,
            b'*': self.handle_array,
            b'%': self.handle_dict
        }

    def handle_request(self,socket_file):
        # Read and process client request
        first_byte = socket_file.read(1)

        print(f"First byte received: {first_byte}")  # Debug first byte

        if not first_byte:
            raise Disconnect()

        try:
             #Delegate to the appropriate handler based on the first byte
             print(f"Looking for handler for: {first_byte}")
             handler = self.handlers[first_byte]
             return handler(socket_file)

        except KeyError:
            print(f"No handler founf for byte: {first_byte}")
            raise CommandError('bad request')
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise

    def handle_simple_string(self, socket_file):
        return socket_file.readline().rstrip('\r\n')
    
    def handle_error(self, socket_file):
        return socket_file.readline().rstrip('\r\n')
    
    def handle_integer(self, socket_file):
        try:
            num_str = socket_file.readline().rstrip(b'\r\n')
            print(f"Readiing integer response: {num_str}")
            #Convert bytes to string then to int
            return int(num_str.decode('utf-8'))
        except ValueError as e:
            print(f"Error parising integer: {e}")
            raise CommandError('invalid integer format')
    
    def handle_string(self, socket_file):
        # First it reads the length ($<length>\r\n)
        try:
            length_str = socket_file.readline().rstrip(b'\r\n')
            print(f"String length received: {length_str}")
            length = int(length_str)
            if length == -1:
                return None # Special-case for Nulls
            length += 2  # Include the trailing \r\n in count
            data = socket_file.read(length)[:-2]
            if isinstance(data, bytes):
                return data.decode('utf-8')
            return data
        except ValueError as e:
            print(f"Error in handle_string:{e}")
            raise CommandError('invalid string format')
    
    def handle_array(self, socket_file):
        try:
            length_str = socket_file.readline().rstrip(b'\r\n')
            print(f"Array length received: {length_str}")
            num_elements = int(length_str)
            print(f"Processing array with {num_elements} elements")
            result = []
            for i in range(num_elements):
                element = self.handle_request(socket_file)
                print(f"Array element {i}: {element}")
                result.append(element)
            return result
        except Exception as e:
            print(f"Error in handle_array: {e}")
            raise

    
    def handle_dict(self, socket_file):
        try:
            num_items = int(socket_file.readline().rstrip(b'\r\n'))
            print(f"Dict with {num_items} items")
            elements = []
            for _ in range(num_items * 2):
                element = self.handle_request(socket_file)
                print(f"Dict element: {element}")
                elements.append(element)
            return dict(zip(elements[::2], elements[1::2]))
        except Exception as e:
            print(f"Error in handle_dict: {e}")
            raise
    
    def write_response(self, socket_file, data):
        # takes serialisable data and write it to a socket connection, handling
        # handling bufferign and serialisation process
        print(f"Writing response for data:{data}")
        buf = BytesIO()
        self._write(buf, data)
        buf.seek(0)
        value = buf.getvalue()
        print(f"Formatted data to send: {value}")
        if isinstance(value, str):
            value =  value.encode('utf-8')
        socket_file.write(value)
        socket_file.flush()
    
    def _write(self, buf, data):
        def write_bytes(data_str):
            buf.write(data_str.encode('utf-8'))

        if data is None:
            write_bytes('$-1\r\n')

        elif isinstance(data, str):
            data = data.encode('utf-8')
            write_bytes('$%d\r\n' % len(data))
            buf.write(data)
            write_bytes('\r\n')
        
        elif isinstance(data, bytes):
            write_bytes('$%d\r\n' % len(data))
            buf.write(data)
            write_bytes('\r\n')

        elif isinstance(data, int):
            write_bytes(':%d\r\n' % data)
        elif isinstance(data, Error):
            write_bytes('-%s\r\n' % data.message)
        elif isinstance(data, (list, tuple)):
            write_bytes('*%d\r\n' % len(data))
            for item in data:
                self._write(buf, item)
        elif isinstance(data, dict):
            write_bytes('%%%d\r\n' % len(data))
            for key in data:
                self._write(buf, key)
                self._write(buf, data[key])
        else:
            raise CommandError('unrecognized type: %s' % type(data))

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

class Client(object):
    def __init__(self, host='127.0.0.1', port=31337):
        self._protocol = ProtocolHandler()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((host, port))
        self._fh = self._socket.makefile('rwb')

    def execute(self, *args):
        print(f"Executing command with args: {args}")
        try:
            self._protocol.write_response(self._fh, args)
            print("Data sent to the server")
            resp = self._protocol.handle_request(self._fh)
            print(f"Response received: {resp}")
            if isinstance(resp, Error):
                raise CommandError(resp.message)
            return resp
        except Exception as e:
            print(f"Error in execute: {str(e)}")
            raise
    
    def get(self, key):
        return self.execute('GET', key)
    
    def set(self, key, value):
        return self.execute('SET', key, value)

    def delete(self, key):
        return self.execute('DELETE', key)
    
    def flush(self):
        return self.execute('FLUSH')
    
    def mget(self, *keys):
        return self.execute('MGET', *keys)
    
    def mset(self, *items):
        return self.execute('MSET', *items)


if __name__ == '__main__':
    from gevent import monkey; monkey.patch_all()
    Server().run()

        
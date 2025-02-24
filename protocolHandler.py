from collections import namedtuple
from io import BytesIO

# Shared exceptions and types
class CommandError(Exception):
    """Raised when an invalid command is received."""
    pass

class Disconnect(Exception):
    """Raised when a client disconnects."""
    pass

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
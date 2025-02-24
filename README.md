# Redis Clone Implementation

## Project Overview
This project implements a Redis-like key-value store using Python, featuring a custom binary protocol for client-server communication. The implementation includes a server that can handle multiple clients concurrently and a client that can interact with the server using various commands.

## Core Components

### Server
The server implementation features:
- A custom protocol handler for processing client requests
- Support for multiple concurrent clients using gevent
- In-memory key-value storage
- Command handling for SET, GET, DELETE, FLUSH, MSET, and MGET operations

### Protocol Design
The protocol uses prefix markers to indicate data types:
- '+' for simple strings
- '-' for errors
- ':' for integers
- '$' for strings/arrays
- '*' for arrays
- '%' for dictionaries

### Key Implementation Challenges

#### 1. Bytes vs Strings Handling
One of the most persistent challenges was maintaining consistency between bytes and string data types. This manifested in several ways:

# Initial problematic code
```
buf.write('*%s\r\n' % len(data))  # TypeError: bytes-like object required
```

# Fixed version
```
def write_bytes(data_str):
    buf.write(data_str.encode('utf-8'))
write_bytes('*%d\r\n' % len(data))
```

The solution involved creating a consistent approach to encoding strings to bytes before writing to buffers and handling bytes appropriately when reading from sockets.

#### 2. Protocol Handler Mapping
Early issues arose from incorrect handler mappings and missing handlers:


# Initial incorrect mapping
```
self.handlers = {
    '$': self.handle_array,  # Wrong handler
}
```

# Fixed mapping
```
self.handlers = {
    '$': self.handle_string,
    '*': self.handle_array,
    '%': self.handle_dict
}
```

#### 3. Null Value Handling
The system initially crashed when attempting to retrieve non-existent keys. This was resolved by implementing proper null handling:

```
def _write(self, buf, data):
    if data is None:
        write_bytes('$-1\r\n')  # Redis protocol for null values
```

#### 4. Nested Data Structures
Handling nested data structures (dictionaries containing arrays or other dictionaries) required careful implementation of recursive processing:

```
def handle_dict(self, socket_file):
    num_items = int(socket_file.readline().rstrip(b'\r\n'))
    elements = [self.handle_request(socket_file) 
               for _ in range(num_items * 2)]
    return dict(zip(elements[::2], elements[1::2]))
```


#### 5. Error Handling
Proper error handling was crucial for maintaining stable connections:
- Command errors needed to be propagated to clients
- Connection issues needed to be handled 
- Protocol parsing errors needed appropriate responses

## Technical Lessons Learned

1. **Binary Protocol Design**
   - Importance of consistent data type handling
   - Need for clear message framing
   - Value of protocol versioning and extensibility

2. **Network Programming**
   - Socket handling in Python
   - Buffered I/O considerations
   - Connection management

3. **Error Handling**
   - Graceful degradation
   - Error propagation through layers
   - Client-side error recovery

4. **Testing Methodology**
   - Unit testing protocol handlers
   - Integration testing client-server communication
   - Edge case identification and handling

## Best Practices Identified

1. **Type Consistency**
   - Maintain clear boundaries between bytes and string data
   - Use consistent encoding/decoding patterns
   - Document type expectations clearly

2. **Error Handling**
   - Implement comprehensive error handling
   - Use appropriate error types
   - Provide meaningful error messages

3. **Debugging**
   - Add detailed logging
   - Implement step-by-step tracing
   - Use clear debug messages

4. **Code Organisation**
   - Separate concerns (protocol, storage, networking)
   - Clear class responsibilities
   - Consistent method naming

## Future Improvements

1. **Performance Optimization**
   - Buffer pooling
   - Connection pooling
   - Protocol optimization

2. **Feature Additions**
   - Persistence
   - Replication
   - More data types
   - Transaction support

3. **Monitoring and Debugging**
   - Better logging
   - Metrics collection
   - Performance monitoring

## Conclusion
This project demonstrates the complexity of implementing a custom binary protocol and the importance of careful type handling in network programming. The challenges encountered and solutions developed provide valuable insights for similar implementations.
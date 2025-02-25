# Redis Clone

## Project Strcuture 
After pulling the repository, you should see the following files: ```
redis_clone/
├── server.py
├── protocol.py
├── client.py
├── exceptions.py
└── README.md
```

---

## Installation 

1. Make sure dependencies have been installed

 ```bash
    pip install gevent
    ```

## Running the Server

1. Start the server by running 

```bash
    python server.py
    ```

2. The server will start listening on **127.0.0.1:31337** (by default)

## Running the Client

You can interact with the client in two ways:  

### 1. **Interactive Python Session** 

```python
$ python
>>> from client import Client
>>> client = Client()
>>> client.set('key', 'value')
1
>>> client.get('key')
'value'
>>> client.set('complex', {'nested': [1, 2, 3]})
1
>>> client.get('complex')
{'nested': [1, 2, 3]}
```

2. Create a Test Script
Create a file test.py:

```
from client import Client

def test_basic_operations():
    client = Client()
    
    # Test SET and GET
    client.set('test_key', 'test_value')
    result = client.get('test_key')
    print(f"SET/GET test: {'Success' if result == 'test_value' else 'Failure'}")
    
    # Test complex data
    complex_data = {'name': 'test', 'values': [1, 2, 3]}
    client.set('complex', complex_data)
    result = client.get('complex')
    print(f"Complex data test: {'Success' if result == complex_data else 'Failure'}")
    
    # Test MSET and MGET
    client.mset('k1', 'v1', 'k2', 'v2', 'k3', 'v3')
    results = client.mget('k1', 'k2', 'k3')
    print(f"MSET/MGET test: {'Success' if results == ['v1', 'v2', 'v3'] else 'Failure'}")
    
    # Test DELETE
    client.delete('k1')
    result = client.get('k1')
    print(f"DELETE test: {'Success' if result is None else 'Failure'}")
    
    # Test FLUSH
    count = client.flush()
    print(f"FLUSH test: {count} keys removed")

if __name__ == '__main__':
    from gevent import monkey; monkey.patch_all()
    test_basic_operations()
```

Then run the script using:  

```bash
python test.py
```

---

## Troubleshooting

### Connection Issues

- Make sure the server is running before starting the client
- Check that the port (31337 by default) is not in use or blocked by a firewall
- If connecting from a different machine, change the host from '127.0.0.1' to the server's IP address

### Protocol Errors

- If you get "bad request" errors, check the protocol implementation
- Make sure both client and server are using the same protocol version
- Debug using the print statements that trace the message flow

---

## **Extensions and Performance Considerations**

An extension to this project could be implementing the following:
- Data persistence (save to disk)
- Authentication - Secure client-server communication.
- Replication (Leader-follower setup) - Leader-follower setup for scalability and fault tolerance.
- Transaction support - Ensure atomicity and consistency.
- TTL for keys - Automatic expiration of keys after a set time.
- Additional data structures (sets, sorted sets, lists)

### Performance Considerations
Optimisations for production environments:  
- Connection pooling
- Buffer management
- Periodic garbage collection
- Monitoring and metrics collection
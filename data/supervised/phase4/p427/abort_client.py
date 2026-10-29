"""Phase 4.27: opens N keep-alive HTTP connections to a backend, then closes them abruptly (TCP reset), as a browser tab does when it is closed or a laptop sleeps. Used only against the private test instance."""
import socket
import struct
import sys
import time

port, n = int(sys.argv[1]), int(sys.argv[2])
socks = []
for _ in range(n):
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n")
    s.recv(4096)
    socks.append(s)
time.sleep(0.5)
for s in socks:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))      # RST on close
    s.close()
print("aborted", n, "connections")

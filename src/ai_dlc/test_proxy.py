"""HTTPS CONNECT allowlisting proxy used only by live conformance containers."""

import ipaddress
import os
import select
import socket
import socketserver


def resolve(host: str) -> list[str]:
    return sorted(
        {str(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    )


def allowed_destination(host, port, allowlist, resolver=resolve):
    if host not in allowlist or port != 443:
        return False
    addresses = resolver(host)
    return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(8192).decode("ascii", errors="replace").strip().split()
        if len(line) != 3 or line[0] != "CONNECT":
            self.wfile.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return
        try:
            host, port_text = line[1].rsplit(":", 1)
            port = int(port_text)
            addresses = resolve(host)
            if not allowed_destination(
                host, port, set(os.environ["ALLOW_HOSTS"].split(",")), lambda _: addresses
            ):
                raise ValueError("denied destination")
            for _ in range(100):
                if self.rfile.readline(8192) in {b"\r\n", b"\n", b""}:
                    break
            else:
                raise ValueError("too many headers")
            # Connect the validated numeric address: a second DNS lookup cannot rebind it.
            remote = socket.create_connection((addresses[0], port), timeout=10)
        except (ValueError, OSError):
            self.wfile.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return
        with remote:
            self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.wfile.flush()
            while True:
                readable, _, _ = select.select([self.connection, remote], [], [], 60)
                if not readable:
                    break
                for stream in readable:
                    data = stream.recv(65536)
                    if not data:
                        return
                    (remote if stream is self.connection else self.connection).sendall(data)


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("0.0.0.0", 8080), Handler) as server:
        server.serve_forever()

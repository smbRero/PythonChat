import threading
import socketserver


MEMBER_COUNT_PREFIX = "c"
MESSAGE_PREFIX = "m"
HOST, PORT = "localhost", 9999
print_mutex = threading.Lock()


def safe_print(lock: threading.Lock, s: str):
    """
    Function to thread-save printing.

    :param lock: Lock object for print
    :param s: string to type
    :return: None
    """
    with lock:
        print(s)


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """
    Request handler object for TCPServer.
    handle() method is called for every new client.
    """

    def handle(self):
        client_name = str(self.request.recv(1024), 'utf-8')
        index = 1
        new_name = client_name

        # name should be unique per chat
        with self.server.names_mutex:
            while new_name in self.server.names:
                index = index + 1
                new_name = f"{client_name}({index})"
            self.server.names.add(new_name)

        safe_print(print_mutex, f"{new_name} connected")
        safe_print(print_mutex, self.client_address)
        with self.server.handlers_mutex:
            self.server.handlers.append(self)
        self.server.send_member_count()
        self.server.send_to_all(self, f"{new_name} joined")
        while True:
            try:
                data = str(self.request.recv(1024), 'utf-8')
                safe_print(print_mutex, "received from client: {}".format(data))
                self.server.send_to_all(self, f"{new_name}: {data}")
            except ConnectionResetError:  # Client disconnected
                with self.server.handlers_mutex:
                    self.server.handlers.remove(self)
                with self.server.names_mutex:
                    self.server.names.remove(new_name)
                self.server.send_to_all(self, f"{new_name} disconnected")
                self.server.send_member_count()
                safe_print(print_mutex, f"Client {self.client_address} disconnected")
                break


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    TCP server object.
    """
    def __init__(self, *args, **kwargs):
        super(ThreadedTCPServer, self).__init__(*args, **kwargs)
        self.handlers = []  # list of handlers
        self.names = set()  # set for client names
        self.names_mutex = threading.Lock()  # Lock for names container
        self.handlers_mutex = threading.Lock()  # Lock for handlers container

    def send_to_all(self, author: ThreadedTCPRequestHandler, message: str):
        data = bytes(MESSAGE_PREFIX, 'ascii')
        data = data + len(message).to_bytes(2, byteorder='big', signed=False)
        data = data + bytes(message, 'utf-8')
        with self.handlers_mutex:
            for client in self.handlers:
                if client is not author:
                    try:
                        client.request.sendall(data)
                    except ConnectionResetError:  # client disconnected
                        continue

    def send_member_count(self):
        data = bytes(MEMBER_COUNT_PREFIX, "ascii")
        with self.handlers_mutex:
            data = data + len(self.handlers).to_bytes(1, byteorder='big', signed=False)
            for client in self.handlers:
                client.request.sendall(data)


def start_server(host, port):
    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    with server:
        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        safe_print(print_mutex, "Server loop running.")
        server.serve_forever()


if __name__ == "__main__":
    start_server(HOST, PORT)

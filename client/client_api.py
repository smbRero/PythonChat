from typing import Callable
import socket
from threading import Thread

HOST, PORT = "localhost", 9999
MEMBER_COUNT_PREFIX = "c"
MESSAGE_PREFIX = "m"


class ClientApiProvider:

    """
    Wrapper class for connection to chat server.

    Methods for the caller:

    - __init__(name: str,
                 message_handler: Callable[[str], None],
                 count_changed_handler: Callable[[int], None],
                 try_reconnect_handler: Callable[[bool], None])
    - try_connect()
    - send_message(message: str)
    - disconnect()

    """

    def __init__(self,
                 name: str,
                 message_handler: Callable[[str], None],
                 count_changed_handler: Callable[[int], None],
                 try_reconnect_handler: Callable[[bool], None]):
        """
        Constructor.

        :param name: member name
        :param message_handler: handler that called after new message received.
        :param count_changed_handler: handler that called after chat member count changed,
        e.g. chat member connected or disconnected.
        :param try_reconnect_handler: handler that called when connection interrupts.
        Called with connected_successfully=False before try, and connected_successfully=True after successful try.
        """

        self._message_handler = message_handler
        self._count_changed_handler = count_changed_handler
        self._try_reconnect_handler = try_reconnect_handler
        self._name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _receiving_loop(self):
        """
        Loop for receiving data from server and passing it to handler.

        :return: None
        """
        while True:
            # Receive data from the server
            try:
                prefix = str(self.sock.recv(1), encoding='ascii')
                if prefix == MEMBER_COUNT_PREFIX:  # Received chat member count
                    member_count = int.from_bytes(self.sock.recv(1), byteorder='big', signed=False)
                    self._count_changed_handler(member_count)
                elif prefix == MESSAGE_PREFIX:  # Received message
                    size = int.from_bytes(self.sock.recv(2), byteorder='big', signed=False)
                    message = str(self.sock.recv(size), "utf-8")
                    self._message_handler(message)
                else:
                    continue
            except ConnectionResetError:  # Server disconnected
                while True:
                    self._try_reconnect_handler(False)
                    self.sock.close()
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        self.sock.connect((HOST, PORT))
                    except ConnectionRefusedError:  # Unsuccessful try
                        continue
                    # Reconnected successfully
                    self.sock.sendall(bytes(self._name, "utf-8"))
                    self._try_reconnect_handler(True)
                    break
            except ConnectionAbortedError:  # Connection aborted by user
                break

    def try_connect(self):
        # Connect to server and send data
        try:
            self.sock.connect((HOST, PORT))
        except ConnectionRefusedError:
            return False
        self.sock.sendall(bytes(self._name, "utf-8"))
        listening_thread = Thread(target=self._receiving_loop)
        listening_thread.start()
        return True

    def send_message(self, message: str):
        """
        Send message to chat members.

        :param message: message text
        :return: None
        """
        self.sock.sendall(bytes(message, "utf-8"))

    def disconnect(self):
        """
        Close connection.

        :return: None
        """
        self.sock.close()

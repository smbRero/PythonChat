from threading import Lock
from client_api import ClientApiProvider

print_mutex = Lock()
can_speak = False


def safe_print(lock: Lock, s: str):
    """
    Function to thread-save printing.

    :param lock: Lock object for print
    :param s: string to type
    :return: None
    """
    lock.acquire()
    print(s)
    lock.release()


def message_handler(msg: str):
    """
    Handler that called after new message received.

    :param msg: message text
    :return: None
    """
    safe_print(print_mutex, msg)


def count_changed_handler(count: int):
    """
    Handler that called after chat member count changed, e.g. chat member connected or disconnected.

    :param count:
    :return:
    """
    # Chat should have at least two active members
    global can_speak
    can_speak = count >= 2
    if not can_speak:
        safe_print(print_mutex, "Too few members. Waiting another member...")


def try_reconnect_handler(connected_successfully: bool):
    """
    Handler that called when connection interrupts.
    Called with connected_successfully=False before try, and connected_successfully=True after successful try.
    :param connected_successfully: shows if connection trying is successfully finished
    :return: None
    """
    if not connected_successfully:
        safe_print(print_mutex, "Server connection failed. Trying to reconnect...")
    else:
        safe_print(print_mutex, "Connected to server again.")


if __name__ == "__main__":
    print("Welcome to the Python Chat! Press Ctrl+C for exit.")
    name = input("Enter your name: ")
    print(f"Hello {name}! Trying to connect... ")
    api = ClientApiProvider(name, message_handler, count_changed_handler, try_reconnect_handler)
    conn_try_count = 0
    try:  # user can interrupt connection trying and chatting with keyboard interrupt

        # Trying to connect until success
        while not api.try_connect():
            conn_try_count = conn_try_count + 1
            print(f"Failed. Trying again({conn_try_count})...")

        safe_print(print_mutex, "Connected to server.")
        while True:
            message = input()
            if can_speak:
                api.send_message(message)
            else:
                safe_print(print_mutex, "Too few members. Waiting another member...")
    except KeyboardInterrupt:
        api.disconnect()

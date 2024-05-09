#!/usr/bin/env python3

import socket
import threading

host = "localhost"
port = 12345


def lora_response(command):
    parts = command.split("=")
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    return "OK" if cmd == "AT" else f"Dummy response to {cmd} with args {args}"


def handle_client(connection, address):
    print(f"Connected by {address}")
    try:
        while True:
            data = connection.recv(1024)
            if not data:
                break

            decoded_command = data.decode().strip()
            response = lora_response(decoded_command)
            connection.sendall(response.encode())
    except Exception as e:
        print(f"Error: {e}")
    finally:
        connection.close()


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Listening on {host}:{port}")

    try:
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client, args=(conn, addr))
            client_thread.start()
    except KeyboardInterrupt:
        print("Server is shutting down.")
    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()

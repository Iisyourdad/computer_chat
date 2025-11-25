import os
import socket
import sys




MESSAGE ="d"






HOST = "10.247.248.102"
PORT = 50007
SECRET = os.environ.get("CHAT_SECRET")

def build_payload(message: str) -> bytes:
    safe_msg = message if message is not None else ""
    return f"{SECRET}|{safe_msg}".encode("utf-8")


def main(msg: str):
    if not SECRET:
        raise SystemExit("Set CHAT_SECRET in your environment to match the receiver before sending.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(build_payload(msg))
    print(f"sent {msg}")


if __name__ == "__main__":
    user_msg = sys.argv[1] if len(sys.argv) > 1 else MESSAGE
    main(user_msg)

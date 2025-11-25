import socket
import struct
import time
from io import BytesIO

from PIL import ImageGrab

HOST = "0.0.0.0"
PORT = 50008
TARGET_FPS = 30
JPEG_QUALITY = 70


def get_local_ip() -> str:
    """Best effort local IP detection for showing in the console."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
            temp.connect(("8.8.8.8", 80))
            return temp.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def capture_frame() -> bytes:
    """Capture the full (multi-monitor) desktop and return it as a JPEG byte string."""
    img = ImageGrab.grab(all_screens=True)
    buff = BytesIO()
    img.save(buff, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buff.getvalue()


def send_frames(conn: socket.socket):
    frame_interval = 1.0 / TARGET_FPS
    while True:
        start = time.perf_counter()
        frame = capture_frame()
        payload = struct.pack("!I", len(frame)) + frame
        conn.sendall(payload)

        elapsed = time.perf_counter() - start
        sleep_for = frame_interval - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)


def main():
    local_ip = get_local_ip()
    print(f"Screen sender ready on {local_ip}:{PORT}")
    print("Waiting for a receiver to connect...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        try:
            while True:
                conn, addr = server.accept()
                print(f"Receiver connected from {addr}, streaming at ~{TARGET_FPS} fps.")
                try:
                    send_frames(conn)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    print("Receiver disconnected. Waiting for the next connection...")
                finally:
                    conn.close()
        except KeyboardInterrupt:
            print("\nShutting down sender.")


if __name__ == "__main__":
    main()

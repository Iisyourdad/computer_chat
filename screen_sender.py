import socket
import struct
import time
from io import BytesIO
import threading

from PIL import ImageGrab

HOST = "0.0.0.0"
PORT = 50008
TARGET_FPS = 30
JPEG_QUALITY = 100
STOP_EVENT = threading.Event()


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
    img = ImageGrab.grab(all_screens=True, include_layered_windows=True)
    buff = BytesIO()
    img.save(buff, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buff.getvalue()


def send_frames(conn: socket.socket):
    frame_interval = 1.0 / TARGET_FPS
    conn.settimeout(1.0)
    first_frame = True
    while not STOP_EVENT.is_set():
        start = time.perf_counter()
        frame = capture_frame()
        if first_frame:
            try:
                from PIL import Image

                with Image.open(BytesIO(frame)) as img:
                    print(f"Streaming resolution: {img.width}x{img.height}")
            except Exception:
                pass
            first_frame = False
        payload = struct.pack("!I", len(frame)) + frame
        try:
            conn.sendall(payload)
        except socket.timeout:
            if STOP_EVENT.is_set():
                break
            continue
        except (ConnectionResetError, BrokenPipeError, OSError):
            break

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
        server.settimeout(1.0)
        try:
            while not STOP_EVENT.is_set():
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                except KeyboardInterrupt:
                    break
                print(f"Receiver connected from {addr}, streaming at ~{TARGET_FPS} fps.")
                try:
                    send_frames(conn)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    print("Receiver disconnected. Waiting for the next connection...")
                finally:
                    conn.close()
        except KeyboardInterrupt:
            pass
    print("\nShutting down sender.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        STOP_EVENT.set()
        print("\nStopped by user.")

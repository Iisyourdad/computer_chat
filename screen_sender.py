import socket
import struct
import time
from io import BytesIO
import threading
import ctypes
from ctypes import wintypes

from PIL import ImageGrab, ImageDraw

HOST = "0.0.0.0"
PORT = 50008
TARGET_FPS = 30
ENCODING = "JPEG"  # Options: "JPEG" or "PNG" (PNG is lossless but larger/slower)
JPEG_QUALITY = 95  # 1-100 for JPEG; higher = better quality, larger size
JPEG_SUBSAMPLING = 0  # 0 = 4:4:4 (best color fidelity), 1 = 4:2:2, 2 = 4:2:0
STOP_EVENT = threading.Event()
CURSOR_RADIUS = 8
CURSOR_COLOR = (255, 64, 64)
CURSOR_OUTLINE = (255, 255, 255)


def get_local_ip() -> str:
    """Best effort local IP detection for showing in the console."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
            temp.connect(("8.8.8.8", 80))
            return temp.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_cursor_pos() -> tuple[int, int] | None:
    point = wintypes.POINT()
    if ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        return point.x, point.y
    return None


def draw_cursor(img, pos: tuple[int, int]):
    x, y = pos
    w, h = img.size
    if x < 0 or y < 0 or x >= w or y >= h:
        return
    r = CURSOR_RADIUS
    draw = ImageDraw.Draw(img)
    draw.ellipse((x - r, y - r, x + r, y + r), outline=CURSOR_OUTLINE, width=2)
    draw.line((x - 2 * r, y, x + 2 * r, y), fill=CURSOR_COLOR, width=2)
    draw.line((x, y - 2 * r, x, y + 2 * r), fill=CURSOR_COLOR, width=2)


def capture_frame() -> bytes:
    """Capture the full (multi-monitor) desktop and return it as an encoded byte string."""
    img = ImageGrab.grab(all_screens=True, include_layered_windows=True)
    pos = get_cursor_pos()
    if pos:
        draw_cursor(img, pos)
    buff = BytesIO()
    if ENCODING.upper() == "PNG":
        img.save(buff, format="PNG", compress_level=3)
    else:
        img.save(
            buff,
            format="JPEG",
            quality=JPEG_QUALITY,
            subsampling=JPEG_SUBSAMPLING,
            optimize=True,
        )
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

import socket
import struct
import sys
import threading
import time
from io import BytesIO

import tkinter as tk
from PIL import Image, ImageTk

SENDER_IP = "127.0.0.1"  # Change this to the sender's IP if not provided on the command line
PORT = 50008


def recv_exact(conn: socket.socket, n: int) -> bytes | None:
    """Read exactly n bytes or return None if the connection is closed."""
    data = bytearray()
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def stream_frames(host: str, on_frame):
    with socket.create_connection((host, PORT), timeout=10) as conn:
        conn.settimeout(5)
        while True:
            length_bytes = recv_exact(conn, 4)
            if not length_bytes:
                break
            frame_len = struct.unpack("!I", length_bytes)[0]
            frame_bytes = recv_exact(conn, frame_len)
            if not frame_bytes:
                break
            on_frame(frame_bytes)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else SENDER_IP

    root = tk.Tk()
    root.title(f"Screen receiver from {host}")
    root.configure(bg="black")

    top_label = tk.Label(
        root,
        text=f"Source: {host}:{PORT}",
        font=("Segoe UI", 12, "bold"),
        bg="black",
        fg="#33ff99",
        anchor="w",
        padx=8,
        pady=4,
    )
    top_label.pack(fill="x")

    image_label = tk.Label(root, bg="black")
    image_label.pack(fill="both", expand=True)

    stop_event = threading.Event()

    def update_frame(frame_bytes: bytes):
        try:
            img = Image.open(BytesIO(frame_bytes))
        except Exception:
            return
        photo = ImageTk.PhotoImage(img)
        image_label.configure(image=photo)
        image_label.image = photo
        root.geometry(f"{img.width}x{img.height}")

    def network_worker():
        while not stop_event.is_set():
            try:
                stream_frames(host, lambda fb: root.after_idle(update_frame, fb))
            except Exception:
                time.sleep(1)
            else:
                time.sleep(1)

    thread = threading.Thread(target=network_worker, daemon=True)
    thread.start()

    def on_close():
        stop_event.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

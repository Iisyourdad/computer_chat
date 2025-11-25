import os
import socket
import threading
import tkinter as tk
from typing import Optional

HOST = "0.0.0.0"
PORT = 50007
POPUP_MARGIN = 4
POPUP_DURATION_MS = 999
REQUIRE_SECRET = os.environ.get("CHAT_SECRET")


def get_local_ip() -> str:
    """Best effort local IP detection for showing in the console."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
            temp.connect(("8.8.8.8", 80))
            return temp.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def show_popup(text: str):
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="black")

    label = tk.Label(
        root,
        text=text,
        font=("Segoe UI", 16, "bold"),
        padx=12,
        pady=12,
        bg="black",
        fg="#33ff99",
    )
    label.pack(fill="both", expand=True)

    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    req_w = label.winfo_reqwidth()
    max_h = max(40, screen_h - 2 * POPUP_MARGIN)
    req_h = min(label.winfo_reqheight(), max_h)
    x = screen_w - req_w - POPUP_MARGIN
    y = max(0, screen_h - req_h - POPUP_MARGIN)
    root.geometry(f"{req_w}x{req_h}+{x}+{y}")

    root.after(POPUP_DURATION_MS, root.destroy)
    root.mainloop()


def parse_and_validate(data: bytes) -> Optional[str]:
    if not REQUIRE_SECRET:
        return None
    try:
        decoded = data.decode("utf-8", errors="ignore")
    except Exception:
        return None

    if "|" not in decoded:
        return None
    provided_secret, raw_msg = decoded.split("|", 1)
    if provided_secret != REQUIRE_SECRET:
        return None
    return raw_msg


def handle_client(conn, addr):
    with conn:
        conn.settimeout(5)
        data = bytearray()
        try:
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data.extend(chunk)
        except Exception:
            return

        msg = parse_and_validate(bytes(data))
        if not msg:
            return

        threading.Thread(target=show_popup, args=(msg,), daemon=True).start()


def main():
    if not REQUIRE_SECRET:
        print("Environment variable CHAT_SECRET is required for authentication. Set it and restart.")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        s.settimeout(1.0)
        public_ip = get_local_ip()
        print(f"Receiver ready on {public_ip}:{PORT} (listening on all interfaces)")
        try:
            while True:
                try:
                    conn, addr = s.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\nShutting down receiver.")


if __name__ == "__main__":
    main()

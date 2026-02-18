import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import concurrent.futures
import queue
from pathlib import Path

import shrink
import image_shrinker

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Media Shrinker")
        self.root.geometry("700x500")

        # Data
        self.files = [] # list of (path, item_id)
        self.processing = False
        self.queue = queue.Queue()

        # GUI Elements
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top Button Frame
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_select = tk.Button(btn_frame, text="Select Files", command=self.select_files, width=15)
        self.btn_select.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_start = tk.Button(btn_frame, text="Start Shrinking", command=self.start_processing, state=tk.DISABLED, width=15, bg="#dddddd")
        self.btn_start.pack(side=tk.LEFT)

        self.btn_clear = tk.Button(btn_frame, text="Clear List", command=self.clear_list, width=10)
        self.btn_clear.pack(side=tk.RIGHT)

        # File List (Treeview)
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("path", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("path", text="File Path")
        self.tree.heading("status", text="Status")
        self.tree.column("path", width=500, anchor="w")
        self.tree.column("status", width=100, anchor="center")

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)

        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscroll=scrollbar_x.set)

        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(10, 5))

        # Status Label
        self.status_lbl = tk.Label(main_frame, text="Ready", anchor="w")
        self.status_lbl.pack(fill=tk.X)

        # Polling loop for thread communication
        self.check_queue()

    def select_files(self):
        filetypes = [
            ("Media Files", "*.mp4 *.jpg *.jpeg *.png"),
            ("Video", "*.mp4"),
            ("Images", "*.jpg *.jpeg *.png"),
            ("All Files", "*.*")
        ]
        filenames = filedialog.askopenfilenames(title="Select Files", filetypes=filetypes)
        if filenames:
            for f in filenames:
                # Avoid exact duplicates in list
                if any(existing[0] == f for existing in self.files):
                    continue
                item_id = self.tree.insert("", tk.END, values=(f, "Pending"))
                self.files.append((f, item_id))

            if self.files:
                self.btn_start.config(state=tk.NORMAL)
                self.status_lbl.config(text=f"{len(self.files)} files loaded.")

    def clear_list(self):
        if self.processing:
            return
        self.tree.delete(*self.tree.get_children())
        self.files = []
        self.btn_start.config(state=tk.DISABLED)
        self.status_lbl.config(text="List cleared.")
        self.progress["value"] = 0

    def start_processing(self):
        if not self.files:
            return

        self.processing = True
        self.btn_select.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)

        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        self.status_lbl.config(text="Processing started...")

        # Start background thread
        threading.Thread(target=self.process_thread, daemon=True).start()

    def process_thread(self):
        images = []
        videos = []

        # Categorize files
        for f, item_id in self.files:
            ext = Path(f).suffix.lower()
            if ext in (".jpg", ".jpeg", ".png"):
                images.append((f, item_id))
            elif ext == ".mp4":
                videos.append((f, item_id))
            else:
                self.queue.put(("update_status", (item_id, "Skipped (Unknown Type)")))
                self.queue.put(("progress", 1))

        # 1. Process Images in Parallel
        # Mark all images as Queued
        for _, item_id in images:
            self.queue.put(("update_status", (item_id, "Queued")))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_item = {
                executor.submit(self.process_single_image, f): item_id
                for f, item_id in images
            }

            for future in concurrent.futures.as_completed(future_to_item):
                item_id = future_to_item[future]
                try:
                    future.result() # Will raise exception if occurred
                    self.queue.put(("update_status", (item_id, "Done")))
                except Exception as e:
                    self.queue.put(("update_status", (item_id, f"Error: {e}")))
                self.queue.put(("progress", 1))

        # 2. Process Videos Sequentially
        for f, item_id in videos:
            self.queue.put(("update_status", (item_id, "Processing...")))
            try:
                self.process_single_video(f)
                self.queue.put(("update_status", (item_id, "Done")))
            except Exception as e:
                self.queue.put(("update_status", (item_id, f"Error: {e}")))
            self.queue.put(("progress", 1))

        self.queue.put(("done", None))

    def process_single_image(self, filepath):
        p = Path(filepath)
        output_dir = p.parent / "output"
        # Directory creation is handled in shrink_image, but explicit check doesn't hurt
        image_shrinker.shrink_image(filepath, str(output_dir))

    def process_single_video(self, filepath):
        p = Path(filepath)
        output_dir = p.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / (p.stem + "_shrunk.mp4")
        shrink.process_video(filepath, str(output_path))

    def check_queue(self):
        try:
            while True:
                msg, data = self.queue.get_nowait()
                if msg == "update_status":
                    item_id, status = data
                    # Check if item exists (in case cleared, though buttons disabled)
                    if self.tree.exists(item_id):
                        self.tree.set(item_id, "status", status)
                        # Ensure row is visible
                        self.tree.see(item_id)
                elif msg == "progress":
                    self.progress["value"] += data
                elif msg == "done":
                    self.processing = False
                    self.btn_select.config(state=tk.NORMAL)
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_clear.config(state=tk.NORMAL)
                    self.status_lbl.config(text="All tasks completed.")
                    messagebox.showinfo("Finished", "Processing complete!")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import time
import os
import sys
import io
import ctypes
import shutil

# --- CẤU HÌNH DPI (Để giao diện không bị mờ trên màn hình 2K/4K) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

# --- FIX LỖI UNICODE TRONG CMD ---
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except: pass

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

# --- IMPORT THƯ VIỆN WIN32 ---
try:
    import win32gui, win32con, win32api, win32process
except ImportError:
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt pywin32:\npip install pywin32")
    sys.exit()

# --- IMPORT THƯ VIỆN AUTO MOUSE/KEY ---
try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button
    from pynput.keyboard import Key
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Loi: pip install pynput (Chức năng đồng bộ sẽ tắt)")

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg="#202020") 
        v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Black.TFrame")
        
        # Style cho frame nền đen
        s = ttk.Style()
        s.configure("Black.TFrame", background="#202020")
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")

class TapGameManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Game V15 - Drag & Drop & Auto Layout")
        self.root.geometry("1400x900")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        if not is_admin():
            messagebox.showwarning("Admin", "Vui lòng chạy Tool bằng quyền Admin để thao tác cửa sổ!")
            self.root.title("⚠ CHƯA CÓ ADMIN ⚠")

        self.current_file_path = None
        self.running_instances = {}
        self.instance_counter = 0
        self.is_master_mouse_running = False
        self.is_master_key_running = False
        self.embedded_hwnds = []
        self.resize_timer = None

        if not shutil.which("java"):
            messagebox.showwarning("Thiếu Java", "Máy chưa cài Java hoặc chưa thêm vào PATH.")

        # XỬ LÝ KÉO THẢ FILE (ARGV)
        self.check_sys_argv()

        self.setup_ui()
        if PYNPUT_AVAILABLE: self.start_input_listeners()
        
        # Bind sự kiện thay đổi kích thước cửa sổ để sắp xếp lại Grid
        self.game_area.bind("<Configure>", self.on_window_resize)

    def check_sys_argv(self):
        # Nếu có tham số truyền vào (do kéo thả file vào exe)
        if len(sys.argv) > 1:
            arg_file = sys.argv[1]
            if os.path.exists(arg_file) and arg_file.lower().endswith(('.jar', '.exe', '.bat')):
                self.current_file_path = arg_file

    def setup_ui(self):
        # KHUNG HIỂN THỊ (TRÁI)
        self.game_area = tk.Frame(self.root, bg="#202020")
        self.game_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.game_container = ScrollableFrame(self.game_area)
        self.game_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.game_grid = self.game_container.scrollable_frame

        # SIDEBAR (PHẢI)
        self.sidebar = tk.Frame(self.root, width=320, bg="#f0f0f0", padx=10, pady=10)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)

        # 1. CẤU HÌNH NGUỒN GAME
        grp_config = ttk.LabelFrame(self.sidebar, text="1. Chọn Game & Số Lượng", padding=10)
        grp_config.pack(fill=tk.X, pady=5)

        ttk.Button(grp_config, text="📄 Chọn File Game (.jar / .exe)", command=self.select_single_file).pack(fill=tk.X, pady=2)
        
        self.lbl_info = tk.Label(grp_config, text="[Chưa chọn game]", fg="blue", wraplength=280)
        self.lbl_info.pack(pady=5)
        
        if self.current_file_path:
            self.lbl_info.config(text=f"File (Auto): {os.path.basename(self.current_file_path)}", fg="green")

        # --- SỐ LƯỢNG (TĂNG/GIẢM) ---
        f_qty = ttk.Frame(grp_config)
        f_qty.pack(fill=tk.X, pady=5)
        ttk.Label(f_qty, text="Số lượng mở:").pack(side=tk.LEFT)
        ttk.Button(f_qty, text="-", width=3, command=self.decrease_qty).pack(side=tk.LEFT, padx=(5, 0))
        self.qty_entry = ttk.Entry(f_qty, width=5, justify='center')
        self.qty_entry.insert(0, "1")
        self.qty_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(f_qty, text="+", width=3, command=self.increase_qty).pack(side=tk.LEFT)
        # ----------------------------

        ttk.Label(grp_config, text="Tên Cửa Sổ Game (BẮT BUỘC):").pack(anchor="w", pady=(10,0))
        self.title_entry = ttk.Entry(grp_config)
        self.title_entry.insert(0, "AngelChip")
        self.title_entry.pack(fill=tk.X)
        tk.Label(grp_config, text="(Nhập 1 phần tên hiển thị trên thanh tiêu đề)", font=("Arial", 8), fg="gray").pack(anchor="w")

        # 2. KÍCH THƯỚC
        grp_param = ttk.LabelFrame(self.sidebar, text="2. Kích Thước Hiển Thị", padding=10)
        grp_param.pack(fill=tk.X, pady=5)
        
        f_size = ttk.Frame(grp_param)
        f_size.pack(fill=tk.X, pady=5)
        ttk.Label(f_size, text="Rộng:").pack(side=tk.LEFT)
        self.width_entry = ttk.Entry(f_size, width=5)
        self.width_entry.insert(0, "320")
        self.width_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(f_size, text="Cao:").pack(side=tk.LEFT)
        self.height_entry = ttk.Entry(f_size, width=5)
        self.height_entry.insert(0, "450")
        self.height_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(self.sidebar, text="▶ CHẠY NGAY", command=self.start_game_instances).pack(fill=tk.X, pady=10)
        ttk.Button(self.sidebar, text="⛔ ĐÓNG HẾT", command=self.stop_all_instances).pack(fill=tk.X)

        # 3. ĐỒNG BỘ
        grp_ctrl = ttk.LabelFrame(self.sidebar, text="3. Đồng Bộ (Mirror)", padding=10)
        grp_ctrl.pack(fill=tk.X, pady=5)
        self.master_mouse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grp_ctrl, text="Link Chuột", variable=self.master_mouse_var, command=self.toggle_modes).pack(anchor="w")
        self.master_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grp_ctrl, text="Link Phím", variable=self.master_key_var, command=self.toggle_modes).pack(anchor="w")

    # --- LOGIC AUTO LAYOUT ---
    def on_window_resize(self, event):
        if self.resize_timer:
            self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(100, self.rearrange_layout)

    def rearrange_layout(self):
        instances = list(self.running_instances.values())
        if not instances: return

        container_width = self.game_area.winfo_width()
        if container_width < 100: return

        try:
            item_width = int(self.width_entry.get()) + 20 
        except:
            item_width = 330
        
        cols = max(1, container_width // item_width)
        
        for i, data in enumerate(instances):
            r = i // cols
            c = i % cols
            data['wrapper'].grid(row=r, column=c, padx=5, pady=5)

    def increase_qty(self):
        try:
            val = int(self.qty_entry.get())
            self.qty_entry.delete(0, tk.END)
            self.qty_entry.insert(0, str(val + 1))
        except ValueError:
            self.qty_entry.insert(0, "1")

    def decrease_qty(self):
        try:
            val = int(self.qty_entry.get())
            if val > 1:
                self.qty_entry.delete(0, tk.END)
                self.qty_entry.insert(0, str(val - 1))
        except ValueError:
            self.qty_entry.insert(0, "1")

    def select_single_file(self):
        fp = filedialog.askopenfilename(filetypes=[("Game", "*.jar *.exe *.bat")])
        if fp:
            self.current_file_path = fp
            self.lbl_info.config(text=f"File: {os.path.basename(fp)}", fg="green")

    # --- HÀM TÌM CỬA SỔ THÔNG MINH (UPDATED) ---
    def find_window(self, pid, title_hint):
        found_hwnd = None
        best_match = None
        
        def cb(hwnd, _):
            nonlocal found_hwnd, best_match
            if not win32gui.IsWindowVisible(hwnd): 
                return True 
            
            txt = win32gui.GetWindowText(hwnd)
            if not txt: return True
            
            # Lọc cửa sổ hệ thống Java rác
            cls_name = win32gui.GetClassName(hwnd)
            if "SunAwtToolkit" in cls_name or "GDI+ Window" in txt or "MSCTFIME UI" in txt:
                return True

            try:
                _, w_pid = win32process.GetWindowThreadProcessId(hwnd)
            except: w_pid = 0

            # ƯU TIÊN 1: Đúng PID và đúng Title
            if w_pid == pid:
                if title_hint and title_hint.lower() in txt.lower():
                    found_hwnd = hwnd
                    return False
                # Nếu đúng PID nhưng Title chưa khớp, tạm lưu vào best_match (dự phòng)
                if best_match is None: best_match = hwnd

            # ƯU TIÊN 2: Đúng Title (trường hợp PID bị lệch do shell=True)
            elif title_hint and title_hint.lower() in txt.lower():
                # Kiểm tra xem cửa sổ này đã được dùng chưa
                if hwnd not in self.embedded_hwnds:
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    if not (style & win32con.WS_CHILD): 
                        # Nếu chưa có best_match hoặc best_match hiện tại không khớp title
                        best_match = hwnd

            return True

        try: win32gui.EnumWindows(cb, None)
        except: pass
        
        return found_hwnd if found_hwnd else best_match

    def embed(self, inst_id, container, proc, title_hint, w, h, is_exe):
        def worker():
            status = self.running_instances[inst_id]['status_label']
            status.config(text="Đang tìm...", fg="blue")
            hwnd = None
            # Tăng thời gian tìm kiếm lên một chút vì Java khởi động chậm
            for i in range(600): 
                # Chú ý: Khi dùng shell=True, proc.poll() có thể trả về ngay lập tức
                # nên ta không check proc.poll() ở đây quá chặt chẽ
                hwnd = self.find_window(proc.pid, title_hint)
                if hwnd: break
                time.sleep(0.1)
            
            self.root.after(0, lambda: self.finalize(inst_id, hwnd, container, w, h))
        threading.Thread(target=worker, daemon=True).start()

    def finalize(self, inst_id, hwnd, container, w, h):
        data = self.running_instances.get(inst_id)
        if not data: return
        if not hwnd:
            data['status_label'].config(text="Không thấy!", fg="red")
            return
        try:
            self.embedded_hwnds.append(hwnd)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style = (style & ~(win32con.WS_POPUP|win32con.WS_CAPTION|win32con.WS_THICKFRAME|win32con.WS_MINIMIZEBOX|win32con.WS_MAXIMIZEBOX)) | win32con.WS_CHILD
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            win32gui.SetParent(hwnd, container.winfo_id())
            win32gui.MoveWindow(hwnd, 0, 0, w, h, True)
            data['hwnd'] = hwnd
            if inst_id == 1: data['status_label'].config(text="MASTER", fg="red")
            else: data['status_label'].config(text="OK", fg="green")
        except Exception as e: 
            print(e)
            data['status_label'].config(text="Lỗi nhúng", fg="red")

    def launch_one_game(self, filepath, w, h, title_hint):
        self.instance_counter += 1
        iid = self.instance_counter
        wrapper = ttk.LabelFrame(self.game_grid, text=f"G{iid}")
        wrapper.grid(row=999, column=999) 
        
        ctrl = ttk.Frame(wrapper)
        ctrl.pack(fill=tk.X)
        sync = tk.BooleanVar(value=True)
        if iid != 1: ttk.Checkbutton(ctrl, variable=sync, text="Link").pack(side=tk.LEFT)
        else: tk.Label(ctrl, text="(Main)", fg="red", font=("Arial",9,"bold")).pack(side=tk.LEFT)
        lbl = tk.Label(ctrl, text="...", fg="orange")
        lbl.pack(side=tk.RIGHT)
        cont = tk.Frame(wrapper, width=w, height=h, bg="black")
        cont.pack()

        try:
            work_dir = os.path.dirname(filepath)
            is_exe = filepath.lower().endswith(".exe")
            
            # --- FIX QUAN TRỌNG: Dùng shell=True để chạy file y như click đúp chuột ---
            # Điều này giúp Windows tự xử lý file jar thiếu manifest
            proc = subprocess.Popen(f'"{filepath}"', cwd=work_dir, shell=True)
            
            self.running_instances[iid] = {'process':proc, 'wrapper':wrapper, 'container':cont, 'status_label':lbl, 'sync_var':sync, 'hwnd':None}
            
            self.rearrange_layout()
            self.embed(iid, cont, proc, title_hint, w, h, is_exe)

        except Exception as e:
            lbl.config(text="Lỗi Run", fg="red")
            messagebox.showerror("Lỗi", f"Không chạy được file:\n{e}")

    def start_game_instances(self):
        if not self.current_file_path:
            messagebox.showwarning("Lỗi", "Vui lòng chọn File game (hoặc kéo thả vào tool)!")
            return
        t = self.title_entry.get().strip()
        if not t:
             messagebox.showwarning("Thiếu Tên", "BẠN PHẢI NHẬP 'Tên Cửa Sổ'!\nTool cần tên để tìm cửa sổ khi dùng chế độ Shell.")
             return
        try:
            qty = int(self.qty_entry.get())
            if qty < 1: qty = 1
        except ValueError:
            messagebox.showwarning("Lỗi", "Số lượng phải là số nguyên dương!")
            return
        w = int(self.width_entry.get())
        h = int(self.height_entry.get())
        def run():
            for i in range(qty):
                self.root.after(0, lambda: self.launch_one_game(self.current_file_path, w, h, t))
                time.sleep(2) 
        threading.Thread(target=run, daemon=True).start()

    def stop_all_instances(self):
        for d in self.running_instances.values():
            try: win32gui.PostMessage(d['hwnd'], win32con.WM_CLOSE, 0, 0)
            except: pass
            try: 
                # Với shell=True, lệnh terminate này có thể chỉ tắt shell, không tắt game
                # Nhưng ta đã gửi WM_CLOSE ở trên nên game sẽ tự tắt
                d['process'].terminate()
            except: pass
            try: d['wrapper'].destroy()
            except: pass
        self.running_instances.clear()
        self.embedded_hwnds.clear()
        self.instance_counter = 0

    def on_closing(self):
        if messagebox.askokcancel("Thoát", "Đóng tool và tắt hết game?"):
            self.stop_all_instances()
            self.root.destroy()
            os._exit(0)

    def toggle_modes(self):
        self.is_master_mouse_running = self.master_mouse_var.get()
        self.is_master_key_running = self.master_key_var.get()

    def start_input_listeners(self):
        def on_click(x, y, button, pressed):
            if not pressed or not self.is_master_mouse_running or button != Button.left: return
            master = self.running_instances.get(1)
            if not master or not master['hwnd']: return
            try:
                c = master['container']
                rx, ry = c.winfo_rootx(), c.winfo_rooty()
                w, h = c.winfo_width(), c.winfo_height()
                if rx<=x<=rx+w and ry<=y<=ry+h:
                    self.broadcast_mouse(x-rx, y-ry)
            except: pass

        def on_key(k, down):
            if not self.is_master_key_running: return
            vk = self.get_vk(k)
            if vk: self.broadcast_key(vk, down, k)

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()
        self.key_listener = keyboard.Listener(on_press=lambda k: on_key(k, True), on_release=lambda k: on_key(k, False))
        self.key_listener.start()

    def broadcast_mouse(self, x, y):
        lp = win32api.MAKELONG(x, y)
        for iid, d in self.running_instances.items():
            if iid == 1 or not d['sync_var'].get(): continue
            hwnd = d['hwnd']
            if hwnd:
                try:
                    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lp)
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
                    time.sleep(0.005)
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
                except: pass

    def broadcast_key(self, vk, down, key_obj):
        scan_code = win32api.MapVirtualKey(vk, 0)
        lparam = (scan_code << 16) | 1
        if key_obj in [Key.up, Key.down, Key.left, Key.right]: lparam |= (1 << 24)
        msg = win32con.WM_KEYDOWN if down else win32con.WM_KEYUP
        if not down: lparam |= (1 << 30); lparam |= (1 << 31)
        for iid, d in self.running_instances.items():
            if iid == 1 or not d['sync_var'].get(): continue
            hwnd = d['hwnd']
            if hwnd: 
                try: win32api.PostMessage(hwnd, msg, vk, lparam)
                except: pass

    def get_vk(self, key):
        if hasattr(key, 'vk'): return key.vk
        specials = {Key.up: 0x26, Key.down: 0x28, Key.left: 0x25, Key.right: 0x27, Key.space: 0x20, Key.enter: 0x0D, Key.esc: 0x1B}
        if key in specials: return specials[key]
        if hasattr(key, 'char') and key.char: return ord(key.char.upper())
        return None

if __name__ == "__main__":
    root = tk.Tk()
    TapGameManager(root)
    root.mainloop()
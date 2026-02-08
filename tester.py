import tkinter as tk
from tkinter import ttk
import subprocess
import os

class ControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Killdozer Control Panel")
        self.root.geometry("800x600")
        self.root.configure(bg='#2e2e2e')
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2e2e2e')
        style.configure('TLabel', background='#2e2e2e', foreground='white')
        style.configure('TButton', background='#3c3c3c', foreground='white')
        style.map('TButton', background=[('active', '#4c4c4c')])
        
        self.create_widgets()
    
    def create_widgets(self):
        
        header = ttk.Frame(self.root)
        header.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(header, text="SYSTEM CONTROL PANEL", font=('Arial', 16)).pack(pady=10)
        
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        info_frame = ttk.LabelFrame(left_frame, text="System Status")
        info_frame.pack(fill='both', expand=True)
        
       
        info_text = """
Hostname: KILLDOZER-PC
OS: Windows 10
CPU Usage: 24%
Memory: 63%
Disk: 55%
Network: Active
        """
        ttk.Label(info_frame, text=info_text).pack(anchor='w', padx=10, pady=10)
        
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        
        control_frame = ttk.LabelFrame(right_frame, text="Quick Actions")
        control_frame.pack(fill='both', expand=True)
        
        buttons = [
            ("Launch Terminal", self.launch_terminal),
            ("System Monitor", self.system_monitor),
            ("File Explorer", self.file_explorer),
            ("Network Config", self.network_config),
            ("Shutdown", self.shutdown),
            ("Restart", self.restart)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(control_frame, text=text, command=command)
            btn.pack(fill='x', pady=2)
        
        
        log_frame = ttk.LabelFrame(self.root, text="System Log")
        log_frame.pack(fill='x', padx=10, pady=5)
        
        log_text = tk.Text(log_frame, height=8, bg='#3c3c3c', fg='white')
        log_text.pack(fill='x', padx=5, pady=5)
        log_text.insert('1.0', "System initialized\n> Security systems: ACTIVE\n> Firewall: ENABLED")
        log_text.configure(state='disabled')
    
    def launch_terminal(self):
        subprocess.Popen(['cmd.exe' if os.name == 'nt' else 'x-terminal-emulator'])
    
    def system_monitor(self):
        subprocess.Popen(['taskmgr.exe' if os.name == 'nt' else 'gnome-system-monitor'])
    
    def file_explorer(self):
        subprocess.Popen(['explorer.exe' if os.name == 'nt' else 'nautilus'])
    
    def network_config(self):
        print("Network configuration dialog would open here")
    
    def shutdown(self):
        self.root.destroy()
    
    def restart(self):
        print("System restart initiated")

if __name__ == "__main__":
    root = tk.Tk()
    app = ControlPanel(root)
    root.mainloop()

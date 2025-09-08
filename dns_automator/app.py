import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import xml.etree.ElementTree as ET
import json
import os
import traceback
import time
import re
import socket
from urllib.parse import urlparse
from threading import Thread, Event
import atexit

BASE_URL = "https://api.namecheap.com/xml.response"
CONFIG_FILE = "config.json"
REQUEST_DELAY = 10
DNS_PROPAGATION_DELAY = 30

class ResultsWindow:
    def __init__(self, parent, results, operation_type="verification"):
        self.window = tk.Toplevel(parent)
        self.window.title("Results Summary")
        self.window.geometry("950x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрирование окна
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # Создание фрейма для результатов
        frame = ttk.Frame(self.window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок в зависимости от типа операции
        if operation_type == "setup":
            title_text = "DNS Setup Results"
        else:
            title_text = "Verification Results Summary"
        
        ttk.Label(frame, text=title_text, 
                 font=("Arial", 14, "bold")).pack(pady=(0, 10))
        
        # Таблица результатов
        columns = ("Domain", "Redirect", "Tracking", "SPF", "DMARC", "Mail Settings", "Verified")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        # Настройка колонок
        tree.heading("Domain", text="Domain")
        tree.heading("Redirect", text="Redirect")
        tree.heading("Tracking", text="Tracking")
        tree.heading("SPF", text="SPF")
        tree.heading("DMARC", text="DMARC")
        tree.heading("Mail Settings", text="Mail Settings")
        tree.heading("Verified", text="Verified")
        
        tree.column("Domain", width=180)
        tree.column("Redirect", width=80, anchor="center")
        tree.column("Tracking", width=80, anchor="center")
        tree.column("SPF", width=80, anchor="center")
        tree.column("DMARC", width=80, anchor="center")
        tree.column("Mail Settings", width=100, anchor="center")
        tree.column("Verified", width=100, anchor="center")
        
        # Добавление данных
        for domain, results_data in results.items():
            status_values = []
            for setting in ["Redirect", "Tracking", "SPF", "DMARC", "Mail Settings"]:
                status = results_data.get(setting, False)
                status_values.append("✓" if status else "✗")
            
            # Проверяем, прошел ли домен верификацию (все поля True)
            is_verified = all(results_data.values())
            status_values.append("✓" if is_verified else "✗")
            
            item_id = tree.insert("", tk.END, values=(domain, *status_values))
            
            # Подсветка строки - темно-зеленый для успеха, темно-красный для неудачи
            if is_verified:
                tree.item(item_id, tags=('success',))
            else:
                tree.item(item_id, tags=('failed',))
        
        # Настройка тегов для подсветки
        tree.tag_configure('success', background='#155724', foreground='white')  # Темно-зеленый
        tree.tag_configure('failed', background='#721c24', foreground='white')   # Темно-красный
        
        # Scrollbar для таблицы
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

class DNSAutomator:
    def __init__(self, root):
        self.root = root
        self.root.title("DNS Automator")
        self.root.geometry("900x700")
        self.config = self.load_config()
        self.setup_ui()
        self.last_api_call = 0
        self.spreadsheet = None
        self.domains_sheet = None
        self.gsuites_sheet = None
        self.processed_domains = []
        self.dmarc_dict = {}
        self.stop_event = Event()
        self.is_running = False
        self.current_operation = None
        self.current_thread = None
        self.verification_results = {}
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        atexit.register(self.cleanup)
        
        self.root.grid_rowconfigure(13, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

    def cleanup(self):
        self.stop_event.set()
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread.join(timeout=2.0)

    def on_closing(self):
        self.cleanup()
        self.root.destroy()

    def get_current_ip(self):
        """Получает текущий внешний IP адрес"""
        try:
            response = requests.get('https://api.ipify.org', timeout=10)
            return response.text.strip()
        except:
            try:
                response = requests.get('https://ident.me', timeout=10)
                return response.text.strip()
            except:
                return None

    def validate_ip(self, ip):
        """Проверяет валидность IPv4 адреса"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False

    def load_config(self):
        """Загружает конфигурацию с обработкой ошибок"""
        config_path = self.get_config_path()
        default_config = {
            "sheet_url": "",
            "api_user": "",
            "api_key": "",
            "username": "",
            "client_ip": "",
            "customer_domain": "",
            "tracking_host": "inst",
            "tracking_value": "prox.itrackly.com",
            "spf": "v=spf1 include:_spf.google.com ~all",
            "mail_enabled": False,
            "keyfile_path": ""
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return default_config
        
    def get_config_path(self):
        """Возвращает путь к конфигу вне EXE"""
        if getattr(sys, 'frozen', False):
            # Если запущен как EXE, сохраняем рядом с EXE
            exe_dir = os.path.dirname(sys.executable)
            return os.path.join(exe_dir, "config.json")
        else:
            # Если запущен как скрипт, используем локальный файл
            return "config.json"

    def save_config(self):
        """Сохраняет конфигурацию с обработкой ошибок"""
        try:
            config_path = self.get_config_path()
            config = {
                "sheet_url": self.entry_sheet.get(),
                "api_user": self.entry_user.get(),
                "api_key": self.entry_key.get(),
                "username": self.entry_username.get(),
                "client_ip": self.entry_ip.get(),
                "customer_domain": self.entry_customer_domain.get(),
                "tracking_host": self.entry_tracking_host.get(),
                "tracking_value": self.entry_tracking_value.get().rstrip('.'),
                "spf": self.entry_spf.get(),
                "mail_enabled": self.mail_var.get(),
                "keyfile_path": self.entry_keyfile.get()
            }
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            messagebox.showinfo("Success", "Configuration saved successfully!")
            
        except Exception as e:
            error_msg = f"Failed to save configuration:\n{str(e)}"
            messagebox.showerror("Configuration Save Error", error_msg)

    def show_error(self, title, message, details=None):
        error_msg = f"{title}\n\n{message}"
        if details:
            error_msg += f"\n\nDetails:\n{details}"
        messagebox.showerror(title, error_msg)
        self.log_message(f"[ERROR] {title}: {message}")

    def log_message(self, message):
        self.text_output.insert(tk.END, message + "\n")
        self.text_output.see(tk.END)
        self.root.update()

    def toggle_ui_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        
        self.btn_save.config(state=state)
        self.btn_clear.config(state=state)
        self.entry_sheet.config(state=state)
        self.entry_user.config(state=state)
        self.entry_key.config(state=state)
        self.entry_username.config(state=state)
        self.entry_ip.config(state=state)
        self.entry_keyfile.config(state=state)
        self.btn_browse.config(state=state)
        self.entry_customer_domain.config(state=state)
        self.entry_tracking_host.config(state=state)
        self.entry_tracking_value.config(state=state)
        self.entry_spf.config(state=state)
        self.chk_mail.config(state=state)
        self.btn_auto_detect.config(state=state)
        
        if enabled:
            self.btn_run.config(text="Run DNS Setup", command=self.run_script, bg="SystemButtonFace")
            self.btn_verify.config(text="Verify All Domains", command=self.verify_all_domains, bg="SystemButtonFace")
            self.btn_run.config(state=tk.NORMAL)
            self.btn_verify.config(state=tk.NORMAL)
        else:
            if self.current_operation == 'setup':
                self.btn_run.config(text="Stop DNS Setup", command=self.stop_script, bg="#ff6b6b")
                self.btn_verify.config(state=tk.DISABLED)
            elif self.current_operation == 'verify':
                self.btn_verify.config(text="Stop Verification", command=self.stop_script, bg="#ff6b6b")
                self.btn_run.config(state=tk.DISABLED)

    @staticmethod
    def validate_domain(domain):
        if not domain:
            return False
        pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
        return re.match(pattern, domain, re.IGNORECASE) is not None

    @staticmethod
    def clean_domain_input(domain):
        domain = (domain or "").strip()
        if not domain:
            return ""
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('://')[1]
        domain = domain.split('/')[0].split('?')[0].split('#')[0]
        domain = domain.split(':')[0]
        return domain.lower()

    def setup_ui(self):
        padx_val = 20
        pady_val = 5

        tk.Label(self.root, text="Google Sheet URL:").grid(row=0, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_sheet = tk.Entry(self.root, width=60)
        self.entry_sheet.grid(row=0, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_sheet.insert(0, self.config.get("sheet_url", ""))

        tk.Label(self.root, text="Namecheap API User:").grid(row=1, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_user = tk.Entry(self.root, width=60)
        self.entry_user.grid(row=1, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_user.insert(0, self.config.get("api_user", ""))

        tk.Label(self.root, text="API Key:").grid(row=2, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_key = tk.Entry(self.root, width=60, show="*")
        self.entry_key.grid(row=2, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_key.insert(0, self.config.get("api_key", ""))

        tk.Label(self.root, text="Username:").grid(row=3, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_username = tk.Entry(self.root, width=60)
        self.entry_username.grid(row=3, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_username.insert(0, self.config.get("username", ""))

        tk.Label(self.root, text="Client IP:").grid(row=4, column=0, sticky="e", padx=padx_val, pady=pady_val)
        
        # Создаем фрейм для IP поля и кнопок
        ip_frame = tk.Frame(self.root)
        ip_frame.grid(row=4, column=1, padx=padx_val, pady=pady_val, sticky="ew")

        # Entry для IP
        self.entry_ip = tk.Entry(ip_frame, width=50)
        self.entry_ip.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry_ip.insert(0, self.config.get("client_ip", ""))

        # Фрейм для кнопок (в стеке)
        ip_buttons_frame = tk.Frame(ip_frame)
        ip_buttons_frame.pack(side=tk.RIGHT, padx=(5, 0))

        # Кнопка для автоматического определения IP
        self.btn_auto_detect = tk.Button(ip_buttons_frame, text="Auto Detect", command=self.auto_detect_ip)
        self.btn_auto_detect.pack()

        tk.Label(self.root, text="Service Account JSON:").grid(row=5, column=0, sticky="e", padx=padx_val, pady=pady_val)
        frame_keyfile = tk.Frame(self.root)
        frame_keyfile.grid(row=5, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_keyfile = tk.Entry(frame_keyfile, width=50)
        self.entry_keyfile.pack(side=tk.LEFT, padx=(0,5), fill=tk.X, expand=True)
        self.entry_keyfile.insert(0, self.config.get("keyfile_path", ""))
        self.btn_browse = tk.Button(frame_keyfile, text="Browse", command=self.browse_file)
        self.btn_browse.pack(side=tk.LEFT)

        tk.Label(self.root, text="Customer Domain (redirect to):").grid(row=7, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_customer_domain = tk.Entry(self.root, width=60)
        self.entry_customer_domain.grid(row=7, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_customer_domain.insert(0, self.config.get("customer_domain", ""))

        tk.Label(self.root, text="Tracking Host:").grid(row=8, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_tracking_host = tk.Entry(self.root, width=60)
        self.entry_tracking_host.grid(row=8, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_tracking_host.insert(0, self.config.get("tracking_host", "inst"))

        tk.Label(self.root, text="Tracking Value:").grid(row=9, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_tracking_value = tk.Entry(self.root, width=60)
        self.entry_tracking_value.grid(row=9, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_tracking_value.insert(0, self.config.get("tracking_value", "prox.itrackly.com").rstrip('.'))

        tk.Label(self.root, text="SPF Record:").grid(row=10, column=0, sticky="e", padx=padx_val, pady=pady_val)
        self.entry_spf = tk.Entry(self.root, width=60)
        self.entry_spf.grid(row=10, column=1, padx=padx_val, pady=pady_val, sticky="ew")
        self.entry_spf.insert(0, self.config.get("spf", "v=spf1 include:_spf.google.com ~all"))

        self.mail_var = tk.BooleanVar()
        self.mail_var.set(self.config.get("mail_enabled", False))
        self.chk_mail = tk.Checkbutton(self.root, text="Enable Mail Settings", variable=self.mail_var)
        self.chk_mail.grid(row=11, column=1, sticky="w", padx=padx_val, pady=pady_val)

        button_frame = tk.Frame(self.root)
        button_frame.grid(row=12, column=1, pady=10, sticky="w")
        self.btn_save = tk.Button(button_frame, text="Save Config", command=self.save_config)
        self.btn_save.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_clear = tk.Button(button_frame, text="Clear Logs", command=self.clear_logs)
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_run = tk.Button(button_frame, text="Run DNS Setup", command=self.run_script)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_verify = tk.Button(button_frame, text="Verify All Domains", command=self.verify_all_domains)
        self.btn_verify.pack(side=tk.LEFT)

        self.text_output = scrolledtext.ScrolledText(self.root, width=100, height=25)
        self.text_output.grid(row=13, column=0, columnspan=2, padx=padx_val, pady=10, sticky="nsew")
        
        # Горячие клавиши для копирования/вставки/вырезания/выделения всего
        self.text_output.bind("<Control-c>", lambda e: self.text_output.event_generate("<<Copy>>"))
        self.text_output.bind("<Control-x>", lambda e: self.text_output.event_generate("<<Cut>>"))
        self.text_output.bind("<Control-v>", lambda e: self.text_output.event_generate("<<Paste>>"))
        self.text_output.bind("<Control-a>", lambda e: (self.text_output.tag_add("sel", "1.0", "end"), "break"))

    def auto_detect_ip(self):
        """Автоматически определяет и устанавливает текущий IP адрес"""
        self.log_message("\n[INFO] Detecting current IP address...")
        current_ip = self.get_current_ip()
        if current_ip:
            self.entry_ip.delete(0, tk.END)
            self.entry_ip.insert(0, current_ip)
            self.log_message(f"[SUCCESS] Detected IP: {current_ip}")
        else:
            self.log_message("[ERROR] Failed to detect IP address")

    def clear_logs(self):
        self.text_output.delete(1.0, tk.END)

    def browse_file(self):
        try:
            filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
            if filename:
                self.entry_keyfile.delete(0, tk.END)
                self.entry_keyfile.insert(0, filename)
                self.save_config()
        except Exception as e:
            self.show_error("File Browse Error", f"Failed to browse for file:\n{str(e)}")

    def stop_script(self):
        self.stop_event.set()
        if self.current_operation == 'setup':
            self.log_message("\n[STOP] Stopping DNS setup process...")
        else:
            self.log_message("\n[STOP] Stopping verification process...")
        self.is_running = False

    def get_case_insensitive(self, row, key):
        for k, v in row.items():
            if k.lower() == key.lower():
                return v
        return ""

    def parse_api_error(self, xml_response):
        try:
            namespaces = {'ns': 'http://api.namecheap.com/xml.response'}
            root = ET.fromstring(xml_response)
            errors = []
            for error in root.findall('.//ns:Errors/ns:Error', namespaces):
                error_number = error.get('Number', '')
                error_text = error.text or ''
                errors.append(f"Code {error_number}: {error_text}")
                
                # Проверка на код ошибки 1011150
                if error_number == "1011150" and "Invalid request IP" in error_text:
                    return "IP_WHITELIST_ERROR"
                    
            return "\n".join(errors) if errors else "Unknown API error"
        except ET.ParseError:
            return f"Invalid API response: {xml_response[:200]}..."

    def namecheap_api(self, command, params):
        if self.stop_event.is_set():
            return None
            
        # Проверка IP адреса перед выполнением запроса
        client_ip = self.entry_ip.get().strip()
        if not self.validate_ip(client_ip):
            self.show_error("IP Error", "Invalid IP address format", "Please enter a valid IPv4 address")
            return None
            
        current_time = time.time()
        elapsed = current_time - self.last_api_call
        if elapsed < REQUEST_DELAY:
            sleep_time = REQUEST_DELAY - elapsed
            self.log_message(f"[PAUSE] Waiting {sleep_time:.1f} seconds before next API call...")
            time.sleep(sleep_time)

        try:
            payload = {
                "ApiUser": self.entry_user.get(),
                "ApiKey": self.entry_key.get(),
                "UserName": self.entry_username.get(),
                "ClientIp": client_ip,
                "Command": command
            }
            payload.update(params)
            
            self.log_message(f"\n[API Request] Sending {command} to {BASE_URL}")
            r = requests.get(BASE_URL, params=payload, timeout=60)
            r.raise_for_status()
            self.last_api_call = time.time()
            
            # Проверка на ошибку IP адреса в ответе API
            if "invalid ip address" in r.text.lower():
                current_real_ip = self.get_current_ip()
                error_msg = f"IP address mismatch! Configured IP: {client_ip}"
                if current_real_ip:
                    error_msg += f", Current real IP: {current_real_ip}"
                self.show_error("IP Mismatch Error", error_msg)
                return None
                
            # Проверка на ошибку 1011150 (IP не в whitelist)
            error_parsed = self.parse_api_error(r.text)
            if error_parsed == "IP_WHITELIST_ERROR":
                self.show_error("IP Whitelist Error", 
                              "Your IP address is not whitelisted in Namecheap", 
                              f"Please add your IP address ({client_ip}) to the Namecheap API whitelist\nDetails: Code 1011150: Invalid request IP")
                self.stop_event.set()
                return None
                
            self.log_message(f"[API Response] Received {len(r.text)} characters")
            return r.text
            
        except requests.RequestException as e:
            error_details = f"URL: {BASE_URL}\nCommand: {command}\nParams: {params}"
            self.show_error("API Communication Error", f"Failed to communicate with Namecheap API:\n{str(e)}", error_details)
            return None
        except Exception as e:
            self.show_error("API Error", f"Unexpected API error:\n{str(e)}")
            return None

    def get_dns_records(self, domain):
        try:
            if not domain:
                return {"status": "error", "message": "Empty domain"}
            
            if not self.validate_domain(domain):
                return {"status": "error", "message": f"Invalid domain format: {domain}"}
            
            sld, tld = domain.split(".", 1)
            
            params = {"SLD": sld, "TLD": tld}
            result = self.namecheap_api("namecheap.domains.dns.getHosts", params)
            
            if result is None:
                return {"status": "error", "message": "API request failed"}
            
            namespaces = {'ns': 'http://api.namecheap.com/xml.response'}
            root = ET.fromstring(result)
            
            email_type = "UNKNOWN"
            domain_result = root.find('.//ns:DomainDNSGetHostsResult', namespaces)
            if domain_result is not None:
                email_type = domain_result.get("EmailType", "UNKNOWN")
            
            if root.attrib.get("Status") == "OK":
                records = []
                for host in root.findall('.//ns:host', namespaces):
                    record = {
                        "Type": host.attrib.get("Type"),
                        "Name": host.attrib.get("Name"),
                        "Address": host.attrib.get("Address"),
                        "TTL": host.attrib.get("TTL")
                    }
                    records.append(record)
                
                return {
                    "status": "success",
                    "message": f"{domain} → DNS records retrieved successfully",
                    "records": records,
                    "email_type": email_type
                }
            else:
                error_msg = self.parse_api_error(result)
                return {"status": "error", "message": f"{domain} → API error", "details": error_msg}
                
        except Exception as e:
            return {"status": "error", "message": f"{domain} → Error", "details": str(e)}

    def verify_all_domains(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Another operation is already in progress.")
            return
            
        self.clear_logs()
        self.log_message("=== Starting Verification for All Domains ===")
        
        self.current_operation = 'verify'
        self.current_thread = Thread(target=self._verify_all_domains_thread)
        self.current_thread.daemon = True
        self.current_thread.start()

    def _verify_all_domains_thread(self):
        self.is_running = True
        self.stop_event.clear()
        self.toggle_ui_state(False)
        self.verification_results = {}
        
        try:
            self.log_message("\n[Google Sheets] Initializing connection...")
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.entry_keyfile.get(), scope)
            client = gspread.authorize(creds)
            
            self.log_message(f"[Google Sheets] Opening spreadsheet: {self.entry_sheet.get()}")
            self.spreadsheet = client.open_by_url(self.entry_sheet.get())
            
            try:
                self.gsuites_sheet = self.spreadsheet.worksheet("G-Suites")
                gsuites_rows = self.gsuites_sheet.get_all_records()
                self.dmarc_dict = {}
                
                for row in gsuites_rows:
                    if self.stop_event.is_set():
                        break
                    domain = self.clean_domain_input(self.get_case_insensitive(row, "Domain"))
                    dmarc = self.get_case_insensitive(row, "DMARC")
                    if domain and dmarc:
                        domain_lower = domain.lower()
                        if domain_lower not in self.dmarc_dict:
                            self.dmarc_dict[domain_lower] = []
                        if dmarc.strip():
                            self.dmarc_dict[domain_lower].append(dmarc.strip())
                
            except Exception as e:
                self.log_message(f"[WARNING] Failed to read G-Suites sheet: {str(e)}")
            
            try:
                self.domains_sheet = self.spreadsheet.worksheet("Domains")
                domains_rows = self.domains_sheet.get_all_records()
                if not domains_rows:
                    raise ValueError("No domains found in Domains sheet")
            except Exception as e:
                raise ValueError(f"Failed to read Domains sheet: {str(e)}")
            
            domains_to_verify = []
            for row in domains_rows:
                if self.stop_event.is_set():
                    self.log_message("\n[STOPPED] Verification process stopped by user")
                    break
                    
                domain = self.clean_domain_input(self.get_case_insensitive(row, "Domain"))
                if domain and self.validate_domain(domain):
                    customer_domain = self.entry_customer_domain.get().strip()
                    redirect_url = f"{customer_domain}?utm_medium=domain_redirect&utm_source=email_outreach&utm_campaign={domain}"
                    domains_to_verify.append({
                        'domain': domain,
                        'redirect_url': redirect_url
                    })
            
            self.processed_domains = domains_to_verify
            self.verify_dns_settings_for_all_domains()
            
        except Exception as e:
            self.show_error("Verification Error", f"Failed to verify domains: {str(e)}")
        finally:
            self.is_running = False
            self.current_operation = None
            self.toggle_ui_state(True)
            
            # Показываем результаты только если процесс не был остановлен на этапе setup
            if self.verification_results and self.current_operation != 'setup':
                ResultsWindow(self.root, self.verification_results, "verification")

    def verify_dns_settings_for_all_domains(self):
        if not self.processed_domains:
            self.log_message("No domains to verify!")
            return
            
        self.log_message(f"\n=== Starting DNS Verification for {len(self.processed_domains)} domains ===")
        
        for domain_info in self.processed_domains:
            if self.stop_event.is_set():
                self.log_message("\n[STOPPED] Verification process stopped by user")
                break
                
            domain = domain_info['domain']
            redirect_url = domain_info['redirect_url']
            
            self.log_message(f"\n[VERIFICATION] Checking DNS records for {domain}...")
            
            result = self.get_dns_records(domain)
            if result["status"] != "success":
                self.log_message(f"[VERIFICATION FAILED] {domain}: {result['message']}")
                self.verification_results[domain] = {
                    "Redirect": False, "Tracking": False, "SPF": False, 
                    "DMARC": False, "Mail Settings": False
                }
                continue
            
            actual_records = result["records"]
            email_type = result.get("email_type", "UNKNOWN")
            
            verification_results = {
                "Redirect": False, "Tracking": False, "SPF": False, 
                "DMARC": False, "Mail Settings": False
            }
            
            mail_settings_ok = email_type == "GMAIL" and self.mail_var.get()
            verification_results["Mail Settings"] = mail_settings_ok
            
            if not mail_settings_ok:
                self.log_message(f"[MAIL SETTINGS ERROR] Expected GMAIL, got: {email_type}")
            
            # Проверка URL redirect
            for record in actual_records:
                if (record["Type"] == "URL301" and record["Name"] in ("@", "") and 
                    redirect_url in record["Address"]):
                    verification_results["Redirect"] = True
                    break
            
            # Проверка CNAME
            tracking_host = self.entry_tracking_host.get().lower()
            tracking_value = self.entry_tracking_value.get().rstrip('.').lower()
            if tracking_host and tracking_value:
                for record in actual_records:
                    if (record["Type"] == "CNAME" and record["Name"].lower() == tracking_host and 
                        record["Address"].rstrip('.').lower() == tracking_value):
                        verification_results["Tracking"] = True
                        break
            
            # Проверка SPF
            spf = self.entry_spf.get()
            if spf:
                for record in actual_records:
                    if (record["Type"] == "TXT" and record["Name"] in ("@", "") and 
                        spf in record["Address"].replace('"', '')):
                        verification_results["SPF"] = True
                        break
            
            # Проверка DMARC
            expected_dmarc_records = self.dmarc_dict.get(domain.lower(), [])
            actual_dmarc_records = []
            
            for record in actual_records:
                if record["Type"] == "TXT" and record["Name"] == "_dmarc":
                    actual_dmarc_records.append(record["Address"].strip().replace('"', ''))
            
            if len(actual_dmarc_records) == len(expected_dmarc_records):
                all_dmarc_correct = True
                for expected_dmarc in expected_dmarc_records:
                    expected_clean = expected_dmarc.strip().replace('"', '')
                    found = False
                    for actual_dmarc in actual_dmarc_records:
                        if expected_clean.lower() == actual_dmarc.lower():
                            found = True
                            break
                    if not found:
                        all_dmarc_correct = False
                        break
                verification_results["DMARC"] = all_dmarc_correct
            
            self.verification_results[domain] = verification_results
            
            try:
                all_data = self.domains_sheet.get_all_values()
                headers = all_data[0]
                
                for i, row in enumerate(all_data[1:], start=2):
                    if len(row) > 0 and row[0].lower() == domain.lower():
                        for col_name, value in verification_results.items():
                            try:
                                col_index = headers.index(col_name)
                                cell_value = "TRUE" if value else "FALSE"
                                self.domains_sheet.update_cell(i, col_index + 1, cell_value)
                            except ValueError:
                                continue
                
                self.log_message(f"[VERIFICATION SUCCESS] {domain} → Sheet updated")
                
            except Exception as e:
                self.log_message(f"[VERIFICATION ERROR] {domain} → Failed to update sheet: {str(e)}")
            
            if domain != self.processed_domains[-1]['domain'] and not self.stop_event.is_set():
                for i in range(REQUEST_DELAY):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        
        self.log_message("\n=== DNS Verification Complete ===")

    def update_dns(self, domain, redirect_url, dmarc_records):
        try:
            if not domain or not self.validate_domain(domain):
                return {"status": "error", "message": "Invalid domain"}
            
            sld, tld = domain.split(".", 1)
            hosts = []

            hosts.append({"Type": "URL301", "Name": "@", "Address": redirect_url})

            tracking_host = self.entry_tracking_host.get()
            tracking_value = self.entry_tracking_value.get().rstrip('.')
            if tracking_host and tracking_value:
                hosts.append({"Type": "CNAME", "Name": tracking_host, "Address": tracking_value})

            spf = self.entry_spf.get()
            if spf:
                hosts.append({"Type": "TXT", "Name": "@", "Address": spf})

            for dmarc in dmarc_records:
                if dmarc:
                    hosts.append({"Type": "TXT", "Name": "_dmarc", "Address": dmarc})

            params = {"SLD": sld, "TLD": tld, "EmailType": "Gmail"}
            
            for i, h in enumerate(hosts, 1):
                params[f"HostName{i}"] = h["Name"]
                params[f"RecordType{i}"] = h["Type"]
                params[f"Address{i}"] = h["Address"]

            self.log_message(f"\n[DNS Update] Processing {domain} with {len(hosts)} records...")
            result = self.namecheap_api("namecheap.domains.dns.setHosts", params)
            
            if result is None:
                return {"status": "error", "message": "API request failed"}
            
            namespaces = {'ns': 'http://api.namecheap.com/xml.response'}
            root = ET.fromstring(result)
            
            if root.attrib.get("Status") == "OK":
                self.processed_domains.append({'domain': domain, 'redirect_url': redirect_url})
                return {"status": "success", "message": f"{domain} → DNS updated successfully"}
            else:
                error_msg = self.parse_api_error(result)
                return {"status": "error", "message": f"{domain} → API error", "details": error_msg}
                
        except Exception as e:
            return {"status": "error", "message": f"{domain} → Error", "details": str(e)}

    def run_script(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Another operation is already in progress.")
            return
            
        self.current_operation = 'setup'
        self.current_thread = Thread(target=self._run_script_thread)
        self.current_thread.daemon = True
        self.current_thread.start()

    def _run_script_thread(self):
        self.is_running = True
        self.stop_event.clear()
        self.toggle_ui_state(False)
        self.clear_logs()
        self.log_message("=== Starting DNS Setup ===")
        self.processed_domains = []
        
        try:
            required_fields = {
                "Google Sheet URL": self.entry_sheet.get(),
                "API User": self.entry_user.get(),
                "API Key": self.entry_key.get(),
                "Username": self.entry_username.get(),
                "Client IP": self.entry_ip.get(),
                "Customer Domain": self.entry_customer_domain.get(),
                "Service Account JSON": self.entry_keyfile.get()
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            customer_domain = self.entry_customer_domain.get().strip()
            
            self.log_message("\n[Google Sheets] Initializing connection...")
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.entry_keyfile.get(), scope)
            client = gspread.authorize(creds)
            
            self.log_message(f"[Google Sheets] Opening spreadsheet: {self.entry_sheet.get()}")
            self.spreadsheet = client.open_by_url(self.entry_sheet.get())
            
            try:
                self.gsuites_sheet = self.spreadsheet.worksheet("G-Suites")
                gsuites_rows = self.gsuites_sheet.get_all_records()
                self.dmarc_dict = {}
                
                for row in gsuites_rows:
                    if self.stop_event.is_set():
                        break
                    domain = self.clean_domain_input(self.get_case_insensitive(row, "Domain"))
                    dmarc = self.get_case_insensitive(row, "DMARC")
                    if domain and dmarc:
                        domain_lower = domain.lower()
                        if domain_lower not in self.dmarc_dict:
                            self.dmarc_dict[domain_lower] = []
                        if dmarc.strip():
                            self.dmarc_dict[domain_lower].append(dmarc.strip())
                
            except Exception as e:
                raise ValueError(f"Failed to read G-Suites sheet: {str(e)}")
            
            try:
                self.domains_sheet = self.spreadsheet.worksheet("Domains")
                domains_rows = self.domains_sheet.get_all_records()
                if not domains_rows:
                    raise ValueError("No domains found in Domains sheet")
            except Exception as e:
                raise ValueError(f"Failed to read Domains sheet: {str(e)}")
            
            results = []
            for i, row in enumerate(domains_rows, 1):
                try:
                    if self.stop_event.is_set():
                        self.log_message("\n[STOPPED] Process stopped by user")
                        break
                        
                    domain = self.clean_domain_input(self.get_case_insensitive(row, "Domain"))
                    if not domain:
                        results.append(f"Row {i} → ERROR: Empty domain value")
                        continue
                    
                    if not self.validate_domain(domain):
                        results.append(f"Row {i} → ERROR: Invalid domain format: {domain}")
                        continue
                    
                    current_redirect = f"{customer_domain}?utm_medium=domain_redirect&utm_source=email_outreach&utm_campaign={domain}"
                    dmarc_records = self.dmarc_dict.get(domain.lower(), [])
                    
                    self.log_message(f"\nProcessing {i}/{len(domains_rows)}: {domain}")
                    self.log_message(f"Redirect URL: {current_redirect}")
                    
                    if self.mail_var.get():
                        self.log_message("Mail settings enabled")
                    
                    result = self.update_dns(domain, current_redirect, dmarc_records)
                    
                    if result["status"] == "success":
                        results.append(result["message"])
                    else:
                        error_msg = f"{result['message']}"
                        if "details" in result:
                            error_msg += f"\nDetails: {result['details']}"
                        results.append(error_msg)
                        self.log_message(f"[ERROR] {error_msg}")
                    
                    if i < len(domains_rows) and not self.stop_event.is_set():
                        for j in range(REQUEST_DELAY):
                            if self.stop_event.is_set():
                                break
                            time.sleep(1)
                            
                except Exception as e:
                    error_msg = f"Row {i} → ERROR: {str(e)}"
                    results.append(error_msg)
                    self.log_message(error_msg)
                    continue
            
            if not self.stop_event.is_set():
                self.log_message("\n=== DNS Setup Complete ===")
                
                if self.processed_domains:
                    self.log_message(f"\n[INFO] Waiting {DNS_PROPAGATION_DELAY} seconds for DNS propagation...")
                    for i in range(DNS_PROPAGATION_DELAY):
                        if self.stop_event.is_set():
                            break
                        time.sleep(1)
                    
                    if not self.stop_event.is_set():
                        self.verify_dns_settings_for_all_domains()
                        # Не показываем результаты при остановке на этапе setup
                        if self.verification_results and not self.stop_event.is_set():
                            ResultsWindow(self.root, self.verification_results, "setup")
                
                self.log_message("\n=== Operation Complete ===")
                self.save_config()
            else:
                self.log_message("\n=== Operation Stopped ===")
                # Не показываем результаты при остановке на этапе setup
                if self.verification_results and self.current_operation != 'setup':
                    ResultsWindow(self.root, self.verification_results, "setup")
            
        except Exception as e:
            self.show_error("Script Error", f"Failed to execute script: {str(e)}")
        finally:
            self.is_running = False
            self.current_operation = None
            self.toggle_ui_state(True)

if __name__ == "__main__":
    root = tk.Tk()
    app = DNSAutomator(root)
    root.mainloop()

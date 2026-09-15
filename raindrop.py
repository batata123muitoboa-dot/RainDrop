import socket
import threading
import time
import webbrowser
import os
import base64
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import filedialog
import pystray
from PIL import Image, ImageDraw

PORTA = 5000

def auto_desanexar():
    if "--bg" not in sys.argv:
        cmd = [sys.executable] + sys.argv + ["--bg"]
        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL
        }
        
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True

        subprocess.Popen(cmd, **kwargs)
        sys.exit(0)

SAVE_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "RainDrop")
os.makedirs(SAVE_DIR, exist_ok=True)

EMOJI_FONT = ("Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji", "DejaVu Sans")

def get_default_gateway():
    if sys.platform == "win32":
        try:
            out = subprocess.check_output("route print 0.0.0.0", shell=True).decode('utf-8', errors='ignore')
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0":
                    return parts[2]
        except Exception:
            pass
        return None
    else:
        try:
            with open("/proc/net/route", "r") as f:
                for line in f:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == '00000000':
                        gw_hex = fields[2]
                        ip_bytes = bytes.fromhex(gw_hex)[::-1]
                        return socket.inet_ntoa(ip_bytes)
        except Exception:
            pass
        return None

def get_meus_ips():
    ips = ['127.0.0.1']
    try:
        hostname = socket.gethostname()
        ips.append(socket.gethostbyname(hostname))
        for addr in socket.getaddrinfo(hostname, None):
            if addr[0] == socket.AF_INET: ips.append(addr[4][0])
    except: pass
    return list(set(ips))

class ConfirmPopup(ctk.CTkToplevel):
    def __init__(self, parent, titulo, mensagem, callback_sim):
        super().__init__(parent)
        self.callback_sim = callback_sim
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        largura, altura = 360, 160
        x = (self.winfo_screenwidth() // 2) - (largura // 2)
        y = (self.winfo_screenheight() // 2) - (altura // 2)
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.configure(fg_color="#0F172A")

        frame = ctk.CTkFrame(self, fg_color="#1E293B", border_width=1, border_color="#334155", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        lbl_titulo = ctk.CTkLabel(frame, text=titulo, font=("Helvetica", 16, "bold"), text_color="#38BDF8")
        lbl_titulo.pack(pady=(16, 4))

        lbl_msg = ctk.CTkLabel(frame, text=mensagem, font=("Helvetica", 13), text_color="#F8FAFC", wraplength=320)
        lbl_msg.pack(pady=(0, 16), padx=16)

        frame_botoes = ctk.CTkFrame(frame, fg_color="transparent")
        frame_botoes.pack(pady=(0, 16))

        btn_nao = ctk.CTkButton(
            frame_botoes, text="Não", width=120, height=36,
            fg_color="#334155", hover_color="#475569", text_color="#F8FAFC",
            font=("Helvetica", 12, "bold"), command=self.destroy
        )
        btn_nao.pack(side="left", padx=8)

        btn_sim = ctk.CTkButton(
            frame_botoes, text="Sim", width=120, height=36,
            fg_color="#0284C7", hover_color="#0369A1", text_color="#F8FAFC",
            font=("Helvetica", 12, "bold"), command=self.aceitar
        )
        btn_sim.pack(side="left", padx=8)

        self.after(10, self.focus_set)

    def aceitar(self):
        self.destroy()
        if self.callback_sim:
            self.callback_sim()

class MenuPopup(ctk.CTkToplevel):
    def __init__(self, parent, variable, x, y):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1E293B")
        self.geometry(f"200x52+{x-170}+{y+35}")
        
        frame = ctk.CTkFrame(self, fg_color="#1E293B", border_width=1, border_color="#334155", corner_radius=8)
        frame.pack(fill="both", expand=True)

        self.chk = ctk.CTkCheckBox(
            frame, 
            text="Receber a si mesmo", 
            variable=variable,
            font=("Helvetica", 12),
            fg_color="#0284C7",
            hover_color="#0369A1",
            text_color="#F8FAFC",
            border_color="#475569",
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=5
        )
        self.chk.pack(padx=14, pady=14, anchor="w")

        self.bind("<FocusOut>", lambda e: self.destroy())
        self.after(10, self.focus_set)

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.overrideredirect(True)
        self.geometry("400x300")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.winfo_screenheight() // 2) - (300 // 2)
        self.geometry(f"400x300+{x}+{y}")
        self.configure(fg_color="#0F172A")

        self.lbl_nome = ctk.CTkLabel(self, text="RainDrop", font=("Helvetica", 32, "bold"), text_color="#0F172A")
        self.lbl_nome.pack(pady=(35, 5))
        
        self.lbl_gota = ctk.CTkLabel(
            self, 
            text="💧", 
            font=(EMOJI_FONT[0], 52), 
            text_color="#0F172A",
            height=70
        )
        self.lbl_gota.pack(pady=0)
        
        self.lbl_slogan = ctk.CTkLabel(self, text="Because Air is overrated.", font=("Helvetica", 14, "italic"), text_color="#0F172A")
        self.lbl_slogan.pack(pady=(5, 30))
        threading.Thread(target=self.animar_splash, daemon=True).start()

    def interpolar_cor(self, cor_inicio_hex, cor_fim_hex, etapas=15):
        r1, g1, b1 = int(cor_inicio_hex[1:3], 16), int(cor_inicio_hex[3:5], 16), int(cor_inicio_hex[5:7], 16)
        r2, g2, b2 = int(cor_fim_hex[1:3], 16), int(cor_fim_hex[3:5], 16), int(cor_fim_hex[5:7], 16)
        return [f"#{int(r1+(r2-r1)*(i/etapas)):02x}{int(g1+(g2-g1)*(i/etapas)):02x}{int(b1+(b2-b1)*(i/etapas)):02x}" for i in range(etapas + 1)]

    def animar_splash(self):
        time.sleep(0.3)
        for cor in self.interpolar_cor("#0F172A", "#38BDF8"):
            self.lbl_gota.configure(text_color=cor)
            time.sleep(0.03)
        time.sleep(0.2)
        for cor in self.interpolar_cor("#0F172A", "#94A3B8"):
            self.lbl_slogan.configure(text_color=cor)
            time.sleep(0.03)
        time.sleep(0.2)
        for cor in self.interpolar_cor("#0F172A", "#F8FAFC"):
            self.lbl_nome.configure(text_color=cor)
            time.sleep(0.03)
        time.sleep(1.2)
        self.destroy()
        self.parent.deiconify()

class RainDropApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("RainDrop")
        self.geometry("480x440")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.receber_si_mesmo = ctk.BooleanVar(value=False)
        self.meus_ips = get_meus_ips()
        self.ultimo_ip_conhecido = None
        self.ultimo_envio = 0
        self.timer_status = None

        SplashScreen(self)

        self.btn_menu = ctk.CTkButton(
            self, text="⋮", width=32, height=32, 
            fg_color="transparent", hover_color="#1E293B", text_color="#94A3B8",
            font=("Helvetica", 20, "bold"), command=self.abrir_menu
        )
        self.btn_menu.place(relx=0.96, rely=0.02, anchor="ne")

        self.label_titulo = ctk.CTkLabel(self, text="💧 RainDrop", font=("Helvetica", 24, "bold"))
        self.label_titulo.pack(pady=(20, 2))

        self.label_slogan = ctk.CTkLabel(self, text="Because Air is overrated.", font=("Helvetica", 12, "italic"), text_color="#94A3B8")
        self.label_slogan.pack(pady=(0, 15))

        self.entry_ip = ctk.CTkEntry(self, placeholder_text="IP (deixe em branco para Auto-Find)", width=360, height=40, corner_radius=10)
        self.entry_ip.pack(pady=6)
        
        self.entry_url = ctk.CTkEntry(self, placeholder_text="https://google.com", width=360, height=40, corner_radius=10)
        self.entry_url.insert(0, "https://google.com")
        self.entry_url.pack(pady=6)

        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(pady=12)

        self.btn_send_link = ctk.CTkButton(
            frame_botoes, text="Mandar Link 🌊", command=self.enviar_link, 
            fg_color="#0284C7", hover_color="#0369A1", width=175, height=42, corner_radius=10,
            font=("Helvetica", 13, "bold")
        )
        self.btn_send_link.pack(side="left", padx=5)

        self.btn_send_img = ctk.CTkButton(
            frame_botoes, text="Mandar Imagem 🖼️", command=self.enviar_imagem, 
            fg_color="#0EA5E9", hover_color="#0284C7", width=175, height=42, corner_radius=10,
            font=("Helvetica", 13, "bold")
        )
        self.btn_send_img.pack(side="left", padx=5)

        self.label_status = ctk.CTkLabel(self, text="Escutando na porta 5000...", text_color="#94A3B8")
        self.label_status.pack(pady=10)

        threading.Thread(target=self.iniciar_servidor_tcp, daemon=True).start()
        threading.Thread(target=self.iniciar_servidor_udp, daemon=True).start()

        self.criar_icone_tray()

    def criar_icone_tray(self):
        image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.polygon([(32, 10), (14, 42), (50, 42)], fill='#0284C7')
        draw.ellipse((14, 26, 50, 58), fill='#0284C7')

        menu = pystray.Menu(
            pystray.MenuItem("Abrir RainDrop", self.mostrar_janela, default=True),
            pystray.MenuItem("Sair", self.encerrar_app)
        )

        self.tray_icon = pystray.Icon("RainDrop", image, "RainDrop", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.esconder_janela)

    def esconder_janela(self):
        self.withdraw()

    def mostrar_janela(self, icon=None, item=None):
        self.deiconify()
        self.focus_force()

    def encerrar_app(self, icon=None, item=None):
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()
        os._exit(0)

    def abrir_menu(self):
        x = self.btn_menu.winfo_rootx()
        y = self.btn_menu.winfo_rooty()
        MenuPopup(self, self.receber_si_mesmo, x, y)

    def resetar_status(self):
        self.label_status.configure(text="Escutando na porta 5000...", text_color="#94A3B8")
        self.timer_status = None

    def atualizar_status(self, texto, cor, temporario=True, delay_ms=2500):
        if self.timer_status:
            self.after_cancel(self.timer_status)
            self.timer_status = None

        self.label_status.configure(text=texto, text_color=cor)

        if temporario:
            self.timer_status = self.after(delay_ms, self.resetar_status)

    def checar_cooldown(self):
        agora = time.time()
        if agora - self.ultimo_envio < 1.0:
            self.atualizar_status("Aguarde um instante...", "#EF4444")
            return False
        self.ultimo_envio = agora
        return True

    def descobrir_dispositivos(self):
        encontrados = set()

        def checar_ip_unicast(target_ip):
            if not self.receber_si_mesmo.get() and target_ip in self.meus_ips:
                return None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.4)
                s.sendto(b"RD_DISCOVERY_REQ", (target_ip, PORTA))
                data, addr = s.recvfrom(512)
                msg = data.decode('utf-8', errors='ignore').strip()
                s.close()
                if msg == "RD_DISCOVERY_RES":
                    return addr[0]
            except Exception:
                pass
            return None

        gw = get_default_gateway()
        if gw:
            res_gw = checar_ip_unicast(gw)
            if res_gw:
                encontrados.add(res_gw)
                self.ultimo_ip_conhecido = res_gw
                return list(encontrados)

        prefixos = set()
        for ip in self.meus_ips:
            if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
                partes = ip.split('.')
                prefixos.add(f"{partes[0]}.{partes[1]}.{partes[2]}.")

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for prefixo in prefixos:
                for i in range(1, 255):
                    futures.append(executor.submit(checar_ip_unicast, f"{prefixo}{i}"))
            for f in futures:
                res = f.result()
                if res:
                    encontrados.add(res)
                    self.ultimo_ip_conhecido = res

        return list(encontrados)

    def enviar_link(self):
        if not self.checar_cooldown(): return

        ip_destino = self.entry_ip.get().strip()
        url = self.entry_url.get().strip()
        if not url:
            self.atualizar_status("Digite uma URL!", "#EF4444")
            return

        def task():
            try:
                self.atualizar_status("Escaneando rede. Aguarde.", "#38BDF8", temporario=False)
                alvos = [ip_destino] if ip_destino and ip_destino != "255.255.255.255" else self.descobrir_dispositivos()

                if not alvos and self.ultimo_ip_conhecido:
                    alvos = [self.ultimo_ip_conhecido]

                if not alvos:
                    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    client.sendto(url.encode('utf-8'), ('255.255.255.255', PORTA))
                    client.close()
                    self.atualizar_status("Broadcast enviado! 🌊", "#22C55E")
                    return

                for ip in alvos:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.settimeout(3)
                    client.connect((ip, PORTA))
                    client.send(url.encode('utf-8'))
                    client.close()

                self.atualizar_status(f"Enviado para {len(alvos)} dispositivo(s)! 🌊", "#22C55E")
            except Exception as e:
                self.atualizar_status(f"Erro: {e}", "#EF4444")

        threading.Thread(target=task).start()

    def enviar_imagem(self):
        if not self.checar_cooldown(): return

        caminho_arquivo = filedialog.askopenfilename(
            title="Selecione uma imagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.webp")]
        )
        if not caminho_arquivo:
            return

        ip_destino = self.entry_ip.get().strip()

        def task():
            try:
                self.atualizar_status("Escaneando rede. Aguarde.", "#38BDF8", temporario=False)
                
                alvos = [ip_destino] if ip_destino and ip_destino != "255.255.255.255" else self.descobrir_dispositivos()

                if not alvos and self.ultimo_ip_conhecido:
                    alvos = [self.ultimo_ip_conhecido]

                if not alvos:
                    self.atualizar_status("Nenhum dispositivo encontrado na rede.", "#EF4444")
                    return

                nome_arquivo = os.path.basename(caminho_arquivo)
                tamanho_bytes = os.path.getsize(caminho_arquivo)

                with open(caminho_arquivo, "rb") as f:
                    dados_imagem = f.read()

                header = f"IMG:{nome_arquivo}:{tamanho_bytes}\n".encode('utf-8')

                for ip in alvos:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.settimeout(10)
                    client.connect((ip, PORTA))
                    client.sendall(header + dados_imagem)
                    client.close()

                self.atualizar_status(f"Imagem enviada para {len(alvos)} dispositivo(s)! 🖼️", "#22C55E")
            except Exception as e:
                self.atualizar_status(f"Erro ao enviar: {e}", "#EF4444")

        threading.Thread(target=task).start()

    def processar_recebimento_seguro(self, tipo, payload, extra_info, addr_str):
        if addr_str not in self.meus_ips:
            self.ultimo_ip_conhecido = addr_str

        if tipo == "LINK":
            if payload.startswith("RD_DISCOVERY"):
                return

            url_formatada = payload if payload.startswith(("http://", "https://")) else f"https://{payload}"
            titulo = "RainDrop: Novo Link"
            mensagem = f"Visitar {url_formatada}?"
            
            def acao_sim():
                self.atualizar_status(f"Link aberto de {addr_str}!", "#38BDF8")
                webbrowser.open(url_formatada)

            self.after(0, lambda: ConfirmPopup(self, titulo, mensagem, acao_sim))

        elif tipo == "IMAGEM":
            filename = payload
            if filename.startswith("RD_DISCOVERY"):
                return

            img_bytes = extra_info
            titulo = "RainDrop: Nova Imagem"
            mensagem = f"Ver imagem {filename}?"

            def acao_sim():
                nome_limpo = os.path.basename(filename)
                caminho_final = os.path.join(SAVE_DIR, f"{int(time.time())}_{nome_limpo}")
                with open(caminho_final, "wb") as f:
                    f.write(img_bytes)
                self.atualizar_status(f"Imagem recebida de {addr_str}! 🖼️", "#38BDF8")
                webbrowser.open(os.path.abspath(caminho_final))

            self.after(0, lambda: ConfirmPopup(self, titulo, mensagem, acao_sim))

    def iniciar_servidor_tcp(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('0.0.0.0', PORTA))
            server.listen(5)
            while True:
                conn, addr = server.accept()
                addr_str = addr[0]

                if not self.receber_si_mesmo.get() and addr_str in self.meus_ips:
                    conn.close()
                    continue

                if addr_str not in self.meus_ips:
                    self.ultimo_ip_conhecido = addr_str

                buffer = bytearray()
                conn.settimeout(5.0)
                try:
                    while b'\n' not in buffer:
                        chunk = conn.recv(1024)
                        if not chunk: break
                        buffer.extend(chunk)
                except socket.timeout:
                    pass

                if buffer.startswith(b"RD_DISCOVERY"):
                    conn.close()
                    continue

                if buffer.startswith(b"IMG:"):
                    if b'\n' in buffer:
                        header_line, rest = buffer.split(b'\n', 1)
                    else:
                        header_line, rest = buffer, bytearray()

                    header_str = header_line.decode('utf-8', errors='ignore').strip()
                    parts = header_str.split(':')
                    
                    if len(parts) >= 2:
                        filename = parts[1]
                        img_data = bytearray(rest)
                        
                        if len(parts) >= 3 and parts[2].isdigit():
                            filesize = int(parts[2])
                            conn.settimeout(10.0)
                            while len(img_data) < filesize:
                                chunk = conn.recv(8192)
                                if not chunk: break
                                img_data.extend(chunk)
                        else:
                            conn.settimeout(10.0)
                            while True:
                                try:
                                    chunk = conn.recv(8192)
                                    if not chunk: break
                                    img_data.extend(chunk)
                                except socket.timeout:
                                    break
                        
                        if img_data:
                            self.processar_recebimento_seguro("IMAGEM", filename, img_data, addr_str)
                else:
                    data_str = buffer.decode('utf-8', errors='ignore').strip()
                    if data_str:
                        self.processar_recebimento_seguro("LINK", data_str, None, addr_str)

                conn.close()
        except Exception as e:
            print(f"[TCP Error] {e}")

    def iniciar_servidor_udp(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            server.bind(('0.0.0.0', PORTA))
            while True:
                data, addr = server.recvfrom(65535)
                if not data: continue
                addr_str = addr[0]
                
                if addr_str not in self.meus_ips:
                    self.ultimo_ip_conhecido = addr_str

                if data.startswith(b"RD_DISCOVERY"):
                    if data.strip() == b"RD_DISCOVERY_REQ":
                        if self.receber_si_mesmo.get() or addr_str not in self.meus_ips:
                            try:
                                resp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                resp_sock.sendto(b"RD_DISCOVERY_RES", (addr_str, addr[1]))
                                resp_sock.sendto(b"RD_DISCOVERY_RES", (addr_str, PORTA))
                                resp_sock.close()
                            except Exception as e:
                                print(f"erro ao responder discovery: {e}")
                    continue

                if not self.receber_si_mesmo.get() and addr_str in self.meus_ips:
                    continue

                if data.startswith(b"IMG:"):
                    try:
                        header_and_data = data[4:]
                        filename_bytes, b64_data = header_and_data.split(b':', 1)
                        filename = filename_bytes.decode('utf-8', errors='ignore')
                        img_bytes = base64.b64decode(b64_data)
                        self.processar_recebimento_seguro("IMAGEM", filename, img_bytes, addr_str)
                    except Exception as e:
                        print(f"erro ao processar imagem UDP: {e}")
                else:
                    dado_str = data.decode('utf-8', errors='ignore').strip()
                    if dado_str:
                        self.processar_recebimento_seguro("LINK", dado_str, None, addr_str)
        except Exception as e: print(f"[UDP ERROR] {e}")

if __name__ == "__main__":
    auto_desanexar()
    app = RainDropApp()
    app.mainloop()
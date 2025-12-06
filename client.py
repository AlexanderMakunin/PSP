import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import time
import datetime
import subprocess
import webbrowser
import shutil
import socket
import queue
import hashlib
import json
import sys
import platform

try:
    import pygame
    pygame.mixer.init()
except ModuleNotFoundError:
    pygame = None

try:
    from cryptography.hazmat.primitives import hashes as crypto_hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
    from cryptography.hazmat.backends import default_backend
except ModuleNotFoundError:
    rsa = None


def start_client():
    root = tk.Tk()
    root.title("Cliente - Panel PSP (mockup)")
    root.geometry("1200x800")

    # Cola de eventos para comunicación hilo->GUI
    event_queue = queue.Queue()

    # Grid principal: top bar, main content, status
    root.columnconfigure(0, weight=0, minsize=240)
    root.columnconfigure(1, weight=1)
    root.columnconfigure(2, weight=0, minsize=320)
    root.rowconfigure(0, weight=0)  # barra superior fija
    root.rowconfigure(1, weight=1)  # contenido
    root.rowconfigure(2, weight=0)  # barra estado

    # Barra superior T1..T5 + Configuración
    top_bar = tk.Frame(root, bg='#ffffff', height=40)
    top_bar.grid(row=0, column=0, columnspan=3, sticky='ew')
    top_bar.grid_propagate(False)

    categorias = [
        ('T1. Procesos', '#1e90ff'),
        ('T2.Threads', '#c71585'),
        ('T3. Sockets', '#ff4500'),
        ('T4. Servicios', '#228b22'),
        ('T5. Seguridad', '#daa520'),
        ('Configuración', '#d3d3d3')
    ]

    def seleccionar_categoria(nombre):
        info_label.config(text=f"Categoría seleccionada: {nombre}")
    # Creamos después info_label; el callback se ejecuta luego y tendrá acceso.

    for i, (texto, color) in enumerate(categorias):
        lbl = tk.Label(top_bar, text=texto, bg=color, fg='white', font=('Helvetica', 11, 'bold'), padx=10, pady=6, cursor='hand2')
        lbl.pack(side='left', padx=(8 if i==0 else 4, 4), pady=4)
        lbl.bind('<Button-1>', lambda e, n=texto: seleccionar_categoria(n))

    # Frames principales
    left = tk.Frame(root, bg="#f8f8f8")
    center = tk.Frame(root, bg="#ffffff")
    right = tk.Frame(root, bg="#ffffff")

    left.grid(row=1, column=0, sticky="nsw", padx=6, pady=(6,6))
    center.grid(row=1, column=1, sticky="nsew", padx=6, pady=(6,6))
    right.grid(row=1, column=2, sticky="nse", padx=6, pady=(6,6))

    left.grid_propagate(False)
    right.grid_propagate(False)

    # LEFT: acciones y listas
    def section(parent, title):
        f = tk.LabelFrame(parent, text=title, padx=6, pady=6)
        f.pack(fill="x", pady=8, padx=8)
        return f

    s_actions = section(left, "")

    # --- funcionalidad adicional ---
    def open_vscode():
        exe = shutil.which('code') or shutil.which('code-insiders') or shutil.which('code-oss')
        if exe:
            try:
                subprocess.Popen([exe])
                info_label.config(text="Abriendo Visual Studio Code...")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir VS Code: {e}")
        else:
            webbrowser.open('https://code.visualstudio.com/')
            info_label.config(text="VS Code no encontrado: abriendo web como alternativa")

    def open_browser():
        url = simpledialog.askstring('Abrir URL', 'Ingresa la URL a abrir:')
        if url and url.strip():
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            try:
                webbrowser.open(url)
                event_queue.put(('status', f'Abierto navegador: {url}'))
            except Exception as e:
                event_queue.put(('status', f'Error: {e}'))

    def buscar_google():
        url = 'https://publicapis.dev/'
        def worker():
            event_queue.put(('status', f'Scraping APIs desde {url}...'))
            try:
                import requests
                from bs4 import BeautifulSoup
                response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extraer APIs con sus URLs
                apis = []
                
                # Buscar todos los links que contengan URLs de APIs
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '').strip()
                    texto = link.get_text().strip()
                    
                    # Filtrar links válidos
                    if (href and (href.startswith('http://') or href.startswith('https://')) and 
                        len(texto) > 2 and len(texto) < 100 and
                        texto not in [t[0] for t in apis]):  # Evitar duplicados por nombre
                        apis.append((texto, href))
                
                # Si no encuentra suficientes, buscar en divs
                if len(apis) < 10:
                    api_elements = soup.find_all(['div', 'section', 'article'])
                    for elem in api_elements[:50]:
                        elem_link = elem.find('a', href=True)
                        if elem_link:
                            href = elem_link.get('href', '').strip()
                            texto = elem.get_text().strip()[:80]
                            if (href and (href.startswith('http://') or href.startswith('https://')) and 
                                len(texto) > 2 and
                                (texto, href) not in apis):
                                apis.append((texto, href))
                
                # Construir resultado - TODAS las APIs con URLs
                resultado = f'\n{"="*70}\n'
                resultado += f'URL: {url}\n'
                resultado += f'{"="*70}\n\n'
                resultado += f'🔗 APIs ENCONTRADAS ({len(apis)})\n'
                resultado += f'{"-"*70}\n'
                if apis:
                    for nombre, api_url in apis:
                        resultado += f'  • {nombre}\n'
                        resultado += f'    URL: {api_url}\n\n'
                else:
                    resultado += '  [No se encontraron]\n'
                resultado += f'{"="*70}\n'
                
                event_queue.put(('scrape_result', resultado))
                event_queue.put(('status', f'✓ APIs encontradas: {len(apis)}'))
            except Exception as e:
                event_queue.put(('scrape_result', f'ERROR AL PROCESAR:\n{str(e)}'))
                event_queue.put(('status', f'✗ Error: {e}'))
        threading.Thread(target=worker, daemon=True, name='APIsScraper').start()


    # Alarma
    def configurar_alarma():
        minutos = simpledialog.askinteger('Alarma', 'Minutos hasta alarma', minvalue=1, maxvalue=720)
        if not minutos:
            return
        def worker():
            target = time.time() + minutos*60
            while True:
                restante = int(target - time.time())
                if restante <= 0:
                    event_queue.put(('alarm', '¡Alarma!'))
                    break
                event_queue.put(('alarm_progress', restante))
                time.sleep(1)
        threading.Thread(target=worker, daemon=True).start()
    tk.Button(s_actions, text='Programar Alarma', bg='#ffe0ff', width=24, command=configurar_alarma).pack(pady=6)
    tk.Button(s_actions, text="Navegar (URL)", bg="#dff0d8", width=24, command=open_browser).pack(pady=6)
    tk.Button(s_actions, text="Buscar API Google", bg="#dff0d8", width=24, command=buscar_google).pack(pady=6)

    # Launch external command with parameters
    def launch_command():
        cmd = simpledialog.askstring("Lanzar comando", "Introduce el comando a ejecutar (ej: firefox https://google.com):")
        if not cmd:
            return
        try:
            # split by shell to allow parameters; run via shell for convenience
            subprocess.Popen(cmd, shell=True)
            info_label.config(text=f"Lanzado: {cmd}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo ejecutar el comando: {e}")

    tk.Button(s_actions, text="Lanzar aplicación (con parámetros)", bg="#e8f4ff", width=30, command=launch_command).pack(pady=6)

    # Execute PowerShell script (.ps1) if pwsh/powershell available
    def run_powershell_script():
        path = filedialog.askopenfilename(title="Selecciona script PowerShell (.ps1)", filetypes=[("PowerShell", "*.ps1" )])
        if not path:
            return
        exe = shutil.which('pwsh') or shutil.which('powershell')
        if not exe:
            messagebox.showwarning("pwsh no encontrado", "No se encontró 'pwsh' ni 'powershell' en PATH. En Linux puedes instalar PowerShell Core (pwsh) o ejecutar el script en Windows.")
            return
        try:
            subprocess.Popen([exe, '-File', path])
            info_label.config(text=f"Ejecutando script PowerShell: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al ejecutar el script: {e}")

    tk.Button(s_actions, text="Ejecutar .ps1 (PowerShell)", bg="#ffeedd", width=30, command=run_powershell_script).pack(pady=6)

    s_apps = section(left, "Aplicaciones")
    tk.Button(s_apps, text="Visual Code", bg="#e6f7ff", width=24, command=open_vscode).pack(pady=4)
    tk.Button(s_apps, text="App2", bg="#e6f7ff", width=24).pack(pady=4)
    tk.Button(s_apps, text="App3", bg="#e6f7ff", width=24).pack(pady=4)

    # Resource monitor and editor
    def open_text_editor():
        ed = tk.Toplevel(root)
        ed.title("Editor - Notepad simple")
        ed.geometry("700x500")
        text = tk.Text(ed)
        text.pack(fill='both', expand=True)

        def save_file():
            p = filedialog.asksaveasfilename(defaultextension='.txt')
            if p:
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(text.get('1.0', 'end'))
                info_label.config(text=f"Fichero guardado: {p}")

        def open_file():
            p = filedialog.askopenfilename()
            if p:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    text.delete('1.0', 'end')
                    text.insert('1.0', f.read())
                info_label.config(text=f"Fichero abierto: {p}")

        btns = tk.Frame(ed)
        btns.pack(fill='x')
        tk.Button(btns, text='Abrir', command=open_file).pack(side='left')
        tk.Button(btns, text='Guardar', command=save_file).pack(side='left')

    tk.Button(s_apps, text="Editor texto", bg="#f0e6ff", width=24, command=open_text_editor).pack(pady=6)
    # Hash archivo
    def hash_archivo():
        path = filedialog.askopenfilename(title='Selecciona archivo para hash')
        if not path:
            return
        def worker():
            event_queue.put(('status', f'Calculando SHA256 de {path}'))
            try:
                h = hashlib.sha256()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                event_queue.put(('hash', f'{path}\nSHA256: {h.hexdigest()}'))
                event_queue.put(('status', 'Hash completado'))
            except Exception as e:
                event_queue.put(('status', f'Error hash: {e}'))
        threading.Thread(target=worker, daemon=True).start()
    tk.Button(s_apps, text='Hash archivo', bg='#e6ffe6', width=24, command=hash_archivo).pack(pady=4)

    def open_resource_monitor():
        # Monitor gráfico sin depender de Pillow: Canvas puro.
        try:
            import psutil
        except ModuleNotFoundError:
            messagebox.showerror("Dependencia falta", "Instala 'psutil' para monitor de recursos: pip install psutil")
            return

        win = tk.Toplevel(root)
        win.title('Monitor recursos (Canvas)')
        width, height = 600, 360
        cv = tk.Canvas(win, width=width, height=height, bg='white')
        cv.pack(fill='both', expand=True)

        # Series
        cpu_data = []
        mem_data = []
        thr_data = []
        maxlen = 120

        def draw_axes():
            cv.delete('axis')
            cv.create_rectangle(50,20,width-20,height-20, outline='#444', tags='axis')
            for i in range(6):
                y = 20 + (height-40)*i/5
                cv.create_line(50,y,width-20,y, fill='#eee', tags='axis')
            cv.create_text(10,20, text='100%', anchor='nw', tags='axis')
            cv.create_text(10,height-40, text='0%', anchor='nw', tags='axis')
            cv.create_text(width-120,10, text='CPU( rojo ) MEM( verde ) HILOS( azul )', anchor='nw', tags='axis')

        def scale_y(val, series_max=100):
            # map 0..series_max to canvas space
            return 20 + (height-40)*(1 - val/series_max)

        def draw_series():
            cv.delete('series')
            # Determine dynamic max for threads
            thr_max = max(thr_data) if thr_data else 1
            def draw_line(data, color, yscale_max):
                if len(data) < 2:
                    return
                step_x = (width-70)/ (maxlen-1)
                pts = []
                start_index = max(0, len(data)-maxlen)
                for idx, val in enumerate(data[start_index:]):
                    x = 50 + step_x*idx
                    y = scale_y(val, yscale_max)
                    pts.append((x,y))
                for i in range(len(pts)-1):
                    cv.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], fill=color, width=2, tags='series')
            draw_line(cpu_data, 'red', 100)
            draw_line(mem_data, 'green', 100)
            draw_line(thr_data, 'blue', thr_max)
            if thr_data:
                cv.create_text(width-180,height-25, text=f'Threads max: {thr_max}', anchor='nw', tags='series', fill='blue')

        def update():
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                thr = sum(p.num_threads() for p in psutil.process_iter())
                cpu_data.append(cpu); mem_data.append(mem); thr_data.append(thr)
                cpu_data[:] = cpu_data[-maxlen:]
                mem_data[:] = mem_data[-maxlen:]
                thr_data[:] = thr_data[-maxlen:]
                draw_axes(); draw_series()
                cv.create_text(60, height-25, text=f'CPU {cpu:.1f}%  MEM {mem:.1f}%  HILOS {thr}', anchor='nw', fill='#222', tags='series')
            except tk.TclError:
                return
            win.after(1000, update)
        draw_axes(); update()

    tk.Button(left, text="Monitor recursos (gráficas)", bg="#fff2cc", width=30, command=open_resource_monitor).pack(pady=6)

    s_batch = section(left, "Procesos batch")
    def realizar_backup():
        # OS-aware backup: Windows uses PowerShell Compress-Archive; Linux uses tar.gz
        src = filedialog.askdirectory(title='Directorio origen a respaldar')
        if not src:
            return
        dest = filedialog.asksaveasfilename(title='Archivo destino backup', defaultextension='.zip' if platform.system()=='Windows' else '.tar.gz')
        if not dest:
            return
        def worker():
            event_queue.put(('status', f'Iniciando backup de {src} -> {dest}'))
            if platform.system()=='Windows':
                exe = shutil.which('powershell') or shutil.which('pwsh')
                if not exe:
                    event_queue.put(('status','PowerShell no encontrado'))
                    return
                # Compress-Archive -Path src -DestinationPath dest
                cmd = [exe, '-Command', f"Compress-Archive -Path '{src}' -DestinationPath '{dest}' -Force"]
                try:
                    subprocess.run(cmd, timeout=600)
                    event_queue.put(('status','Backup completado (Windows)'))
                except Exception as e:
                    event_queue.put(('status', f'Error backup: {e}'))
            else:
                # Linux/Unix: tar -czf dest -C parent basename
                import os
                parent = os.path.dirname(src)
                base = os.path.basename(src)
                cmd = ['tar','-czf',dest,'-C',parent,base]
                try:
                    subprocess.run(cmd, timeout=600)
                    event_queue.put(('status','Backup completado (tar.gz)'))
                except Exception as e:
                    event_queue.put(('status', f'Error backup: {e}'))
        threading.Thread(target=worker, daemon=True).start()
    tk.Button(s_batch, text="Copias de seguridad", bg="#fff0d6", width=24, command=realizar_backup).pack(pady=6)

    # CENTER: Notebook grande + panel inferior
    center.rowconfigure(0, weight=1)
    center.rowconfigure(1, weight=0)
    center.columnconfigure(0, weight=1)

    notebook = ttk.Notebook(center)
    notebook.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

    # store text widgets so we can update a specific tab programmatically
    tab_texts = {}
    tab_names = ["Resultados", "Navegador", "Correos", "Tareas", "Alarmas", "Enlaces", "Servicios", "Seguridad"]
    for name in tab_names:
        f = ttk.Frame(notebook)
        notebook.add(f, text=name)
        
        # Añadir botones ANTES del área de texto para que sean visibles
        if name == 'Navegador':
            tk.Label(f, text='Herramientas de navegación:', font=('Arial', 10, 'bold')).pack(anchor='w', padx=6, pady=4)
            nav_frame = tk.Frame(f)
            nav_frame.pack(anchor='w', padx=6, pady=4)
            
            def abrir_url_navegador():
                url = simpledialog.askstring('Abrir URL', 'Ingresa la URL a abrir:')
                if url and url.strip():
                    url = url.strip()
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    try:
                        webbrowser.open(url)
                        event_queue.put(('status', f'Abriendo: {url}'))
                    except Exception as e:
                        event_queue.put(('status', f'Error: {e}'))
            
            def iniciar_scraping():
                url = simpledialog.askstring('Web Scraping', 'Ingresa la URL a escanear:')
                if url and url.strip():
                    url = url.strip()
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    def worker():
                        event_queue.put(('status', f'Scraping: {url}...'))
                        try:
                            import requests, re
                            from bs4 import BeautifulSoup
                            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Extraer emails
                            emails = sorted(list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', response.text))))
                            
                            # Extraer teléfonos
                            telefonos = sorted(list(set(re.findall(r'(?:\+?\d{1,3}[-.]?)?\(?\d{2,4}\)?[-.]?\d{2,4}[-.]?\d{2,4}|\d{9,}', response.text))))
                            telefonos = [t for t in telefonos if len(t) >= 9]
                            
                            # Extraer nombres/títulos
                            nombres = set()
                            for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'b', 'strong', 'a']):
                                texto = elem.get_text().strip()
                                if 2 <= len(texto) <= 50:
                                    nombres.add(texto)
                            nombres = sorted(list(nombres))[:30]
                            
                            # Construir resultado con mejor formato
                            resultado = f'\n{"="*70}\n'
                            resultado += f'URL: {url}\n'
                            resultado += f'{"="*70}\n\n'
                            
                            # Sección de Emails
                            resultado += f'📧 EMAILS ({len(emails)})\n'
                            resultado += f'{"-"*70}\n'
                            if emails:
                                for e in emails[:15]:
                                    resultado += f'  {e}\n'
                                if len(emails) > 15:
                                    resultado += f'\n  ... y {len(emails)-15} más\n'
                            else:
                                resultado += '  [No se encontraron]\n'
                            resultado += '\n'
                            
                            # Sección de Teléfonos
                            resultado += f'📞 TELÉFONOS ({len(telefonos)})\n'
                            resultado += f'{"-"*70}\n'
                            if telefonos:
                                for t in telefonos[:15]:
                                    resultado += f'  {t}\n'
                                if len(telefonos) > 15:
                                    resultado += f'\n  ... y {len(telefonos)-15} más\n'
                            else:
                                resultado += '  [No se encontraron]\n'
                            resultado += '\n'
                            
                            # Sección de Títulos/Nombres
                            resultado += f'👥 TÍTULOS/NOMBRES ({len(nombres)})\n'
                            resultado += f'{"-"*70}\n'
                            if nombres:
                                for n in nombres[:20]:
                                    resultado += f'  {n}\n'
                                if len(nombres) > 20:
                                    resultado += f'\n  ... y {len(nombres)-20} más\n'
                            else:
                                resultado += '  [No se encontraron]\n'
                            resultado += f'\n{"="*70}\n'
                            
                            event_queue.put(('scrape_result', resultado))
                            event_queue.put(('status', f'✓ Completado: {len(emails)} emails, {len(telefonos)} telefonos'))
                        except Exception as e:
                            event_queue.put(('scrape_result', f'ERROR AL PROCESAR:\n{str(e)}'))
                            event_queue.put(('status', f'✗ Error: {e}'))
                    threading.Thread(target=worker, daemon=True, name='Scraper').start()
            
            tk.Button(nav_frame, text='🌐 Abrir URL', bg='#87CEEB', font=('Arial', 10, 'bold'), command=abrir_url_navegador).pack(side='left', padx=2)
            tk.Button(nav_frame, text='🔍 Extraer Datos', bg='#FFB6C1', font=('Arial', 10, 'bold'), command=iniciar_scraping).pack(side='left', padx=2)
        
        if name == 'Tareas':
            btn_frame = tk.Frame(f)
            btn_frame.pack(anchor='w', padx=6, pady=4)
            tk.Button(btn_frame, text='🏁 Iniciar Carrera de Camellos', bg='#90EE90', font=('Arial', 10, 'bold'), 
                     command=lambda: iniciar_carrera(tab_texts['Tareas'])).pack(side='left', padx=2)
        
        if name == 'Servicios':
            srv_frame = tk.Frame(f)
            srv_frame.pack(anchor='w', padx=6, pady=4)
            tk.Button(srv_frame, text='POP3 listar', command=lambda: servicio_pop3()).pack(side='left', padx=2)
            tk.Button(srv_frame, text='SMTP enviar', command=lambda: servicio_smtp()).pack(side='left', padx=2)
            tk.Button(srv_frame, text='FTP listar', command=lambda: servicio_ftp()).pack(side='left', padx=2)
            tk.Button(srv_frame, text='HTTP GET', command=lambda: consumir_api('https://httpbin.org/get')).pack(side='left', padx=2)
        
        if name == 'Seguridad':
            sec_frame = tk.Frame(f)
            sec_frame.pack(anchor='w', padx=6, pady=4)
            tk.Button(sec_frame, text='Generar RSA', command=lambda: generar_rsa()).pack(side='left', padx=2)
            tk.Button(sec_frame, text='AES Cifrar', command=lambda: aes_cifrar()).pack(side='left', padx=2)
        
        # Área de texto después de los botones
        txt = tk.Text(f)
        txt.insert("1.0", f"{name} - área de contenido\n\n")
        txt.pack(fill="both", expand=True, padx=6, pady=6)
        tab_texts[name] = txt

    info = tk.Frame(center, bg="#f7fff0", height=120)
    info.grid(row=1, column=0, sticky="ew", padx=6, pady=(0,6))
    info.grid_propagate(False)
    info_label = tk.Label(info, text="Panel para notas informativas y mensajes sobre la ejecución de los hilos.", bg="#f7fff0", anchor="w")
    info_label.pack(fill='both', expand=True, padx=8, pady=8)

    # RIGHT: Chat y lista de alumnos
    chat_box = tk.LabelFrame(right, text="Chat", padx=6, pady=6)
    chat_box.pack(fill="x", padx=8, pady=(8,4))
    tk.Label(chat_box, text="Mensaje").pack(anchor="w")
    msg = tk.Text(chat_box, height=6)
    msg.pack(fill="x", pady=4)
    tk.Button(chat_box, text="enviar", bg="#cfe8cf").pack(pady=(0,6))

    students = tk.LabelFrame(right, text="Alumnos", padx=6, pady=6)
    students.pack(fill="both", expand=True, padx=8, pady=(4,8))
    for i in range(1, 4):
        s = tk.Frame(students)
        s.pack(fill="x", pady=6)
        tk.Label(s, text=f"Alumno {i}", font=("Helvetica", 13, "bold")).pack(anchor="w")
        tk.Label(s, text="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod.", wraplength=280, justify="left").pack(anchor="w")

    # Reproductor música
    music_state = {'path': None, 'thread': None, 'playing': False, 'stopping': False}
    def seleccionar_musica():
        p = filedialog.askopenfilename(title='Seleccionar audio', filetypes=[('Audio','*.wav *.mp3 *.ogg'), ('Todos','*.*')])
        if p:
            music_state['path'] = p
            info_label.config(text=f'Audio: {p}')
    def reproducir_musica():
        if pygame is None:
            messagebox.showwarning('Audio', 'Instala pygame: pip install pygame')
            return
        path = music_state.get('path')
        if not path:
            seleccionar_musica(); path = music_state.get('path')
            if not path:
                return
        if pygame.mixer.music.get_busy():
            event_queue.put(('status', 'Ya reproduciendo'))
            return
        music_state['stopping'] = False
        def worker():
            event_queue.put(('status', f'Reproduciendo {path}'))
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                music_state['playing'] = True
                # Esperar mientras reproduce y no se detiene
                while pygame.mixer.music.get_busy() and not music_state['stopping']:
                    time.sleep(0.1)
                if not music_state['stopping']:
                    event_queue.put(('status', 'Audio terminado'))
                music_state['playing'] = False
            except Exception as e:
                event_queue.put(('status', f'Error audio: {e}'))
                music_state['playing'] = False
        t = threading.Thread(target=worker, daemon=True); music_state['thread']=t; t.start()
    def detener_musica():
        try:
            if pygame and pygame.mixer.music.get_busy():
                music_state['stopping'] = True
                pygame.mixer.music.stop()
                event_queue.put(('status', 'Audio detenido'))
            else:
                event_queue.put(('status', 'No hay audio reproduciéndose'))
        except Exception as e:
            event_queue.put(('status', f'Error al detener: {e}'))
    music_box = tk.LabelFrame(right, text='Reproductor música', padx=4, pady=4)
    music_box.pack(fill='x', padx=8, pady=(0,8))
    tk.Button(music_box, text='Seleccionar', command=seleccionar_musica).pack(side='left', padx=2)
    tk.Button(music_box, text='Play', command=reproducir_musica).pack(side='left', padx=2)
    tk.Button(music_box, text='Stop', command=detener_musica).pack(side='left', padx=2)

    # Chat cliente
    chat_client = {'sock': None}
    def conectar_chat():
        if chat_client['sock']:
            messagebox.showinfo('Chat','Ya conectado')
            return
        host = simpledialog.askstring('Host','Host chat', initialvalue='127.0.0.1')
        port = simpledialog.askinteger('Puerto','Puerto', initialvalue=3333)
        if not host or not port:
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            chat_client['sock']=s
            event_queue.put(('status', f'Chat conectado {host}:{port}'))
            def receptor():
                try:
                    while True:
                        data = s.recv(1024)
                        if not data:
                            break
                        event_queue.put(('chat', data.decode(errors='ignore')))
                except Exception as e:
                    event_queue.put(('status', f'Error chat: {e}'))
                finally:
                    s.close(); chat_client['sock']=None
                    event_queue.put(('status','Chat desconectado'))
            threading.Thread(target=receptor, daemon=True).start()
        except Exception as e:
            messagebox.showerror('Chat', f'Error conexión: {e}')
    def enviar_chat():
        texto = msg.get('1.0','end').strip()
        if not texto:
            return
        s = chat_client.get('sock')
        if not s:
            messagebox.showwarning('Chat','No conectado')
            return
        try:
            s.send(texto.encode())
            msg.delete('1.0','end')
        except Exception as e:
            event_queue.put(('status', f'Error envío: {e}'))
    tk.Button(chat_box, text='Conectar', bg='#ddeeff', command=conectar_chat).pack(pady=(0,4))
    tk.Button(chat_box, text='Enviar mensaje', bg='#cfe8cf', command=enviar_chat).pack(pady=(0,6))

    # Sección Sockets (TCP/UDP servers) añadida al panel izquierdo
    s_sockets = section(left, 'Sockets Locales')
    tcp_state = {'thread': None, 'stop': False, 'sock': None}
    udp_state = {'thread': None, 'stop': False, 'sock': None}

    def start_tcp_server():
        if tcp_state['thread'] and tcp_state['thread'].is_alive():
            info_label.config(text='TCP Server ya iniciado')
            return
        port = simpledialog.askinteger('TCP Server','Puerto', initialvalue=5555)
        if not port:
            return
        def worker():
            event_queue.put(('status', f'TCP Server escuchando {port}'))
            import socket as s
            srv = s.socket(s.AF_INET, s.SOCK_STREAM)
            srv.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR,1)
            srv.bind(('0.0.0.0', port))
            srv.listen(5)
            tcp_state['sock']=srv
            while not tcp_state['stop']:
                try:
                    srv.settimeout(1.0)
                    try:
                        c, addr = srv.accept()
                    except s.timeout:
                        continue
                    event_queue.put(('status', f'Nueva conexión TCP {addr}'))
                    threading.Thread(target=lambda: manejar_tcp_cliente(c, addr), daemon=True).start()
                except Exception as e:
                    event_queue.put(('status', f'Error server TCP: {e}'))
                    break
            srv.close(); tcp_state['sock']=None; tcp_state['stop']=False
            event_queue.put(('status','TCP Server detenido'))
        tcp_state['stop']=False
        t = threading.Thread(target=worker, daemon=True); tcp_state['thread']=t; t.start()

    def manejar_tcp_cliente(c, addr):
        try:
            while True:
                data = c.recv(1024)
                if not data:
                    break
                event_queue.put(('status', f'TCP {addr} -> {data[:40]!r}'))
                c.send(b'ACK')
        except Exception as e:
            event_queue.put(('status', f'Error cliente TCP {addr}: {e}'))
        finally:
            c.close()

    def stop_tcp_server():
        tcp_state['stop']=True

    def start_udp_server():
        if udp_state['thread'] and udp_state['thread'].is_alive():
            info_label.config(text='UDP Server ya iniciado')
            return
        port = simpledialog.askinteger('UDP Server','Puerto', initialvalue=5556)
        if not port:
            return
        def worker():
            event_queue.put(('status', f'UDP Server escuchando {port}'))
            import socket as s
            srv = s.socket(s.AF_INET, s.SOCK_DGRAM)
            srv.bind(('0.0.0.0', port))
            udp_state['sock']=srv
            srv.settimeout(1.0)
            while not udp_state['stop']:
                try:
                    try:
                        data, addr = srv.recvfrom(1024)
                    except s.timeout:
                        continue
                    event_queue.put(('status', f'UDP {addr} -> {data[:40]!r}'))
                    srv.sendto(b'ACK', addr)
                except Exception as e:
                    event_queue.put(('status', f'Error server UDP: {e}'))
                    break
            srv.close(); udp_state['sock']=None; udp_state['stop']=False
            event_queue.put(('status','UDP Server detenido'))
        udp_state['stop']=False
        t = threading.Thread(target=worker, daemon=True); udp_state['thread']=t; t.start()

    def stop_udp_server():
        udp_state['stop']=True

    tk.Button(s_sockets, text='Start TCP', bg='#e0ffe0', command=start_tcp_server).pack(pady=2, fill='x')
    tk.Button(s_sockets, text='Stop TCP', bg='#ffe0e0', command=stop_tcp_server).pack(pady=2, fill='x')
    tk.Button(s_sockets, text='Start UDP', bg='#e0ffe0', command=start_udp_server).pack(pady=2, fill='x')
    tk.Button(s_sockets, text='Stop UDP', bg='#ffe0e0', command=stop_udp_server).pack(pady=2, fill='x')

    # Carrera camellos con sincronización mejorada
    race_state = {'running': False, 'winner': None, 'lock': threading.Lock(), 'condition': threading.Condition()}
    
    def iniciar_carrera(text_widget):
        # Verificar si ya hay una carrera en curso
        with race_state['lock']:
            if race_state['running']:
                event_queue.put(('status', 'Ya hay una carrera en curso'))
                return
            race_state['running'] = True
            race_state['winner'] = None
        
        corredores = 5
        posiciones = [0] * corredores
        meta = 50
        ganador_declarado = threading.Event()
        
        def corredor(i):
            import random
            nombre = f"Camello {i+1}"
            try:
                while not ganador_declarado.is_set():
                    # Sincronización: solo un corredor avanza a la vez
                    with race_state['lock']:
                        # Verificar si alguien ya ganó
                        if ganador_declarado.is_set():
                            break
                        
                        # Avanzar
                        avance = random.randint(1, 3)
                        posiciones[i] += avance
                        
                        # Actualizar visualización
                        event_queue.put(('race_update', (i, posiciones[i], meta)))
                        
                        # Verificar si alcanzó la meta
                        if posiciones[i] >= meta and not ganador_declarado.is_set():
                            ganador_declarado.set()
                            race_state['winner'] = i
                            event_queue.put(('race_end', i))
                            break
                    
                    # Esperar un poco antes del siguiente avance
                    time.sleep(random.uniform(0.1, 0.2))
            except Exception as e:
                event_queue.put(('status', f'Error en {nombre}: {e}'))
            finally:
                # Asegurar que liberamos recursos
                with race_state['lock']:
                    pass
        
        # Iniciar todos los corredores
        event_queue.put(('race_start', corredores))
        for i in range(corredores):
            threading.Thread(target=corredor, args=(i,), daemon=True, name=f'Corredor-{i+1}').start()
        
        # Thread que monitorea finalización
        def monitor_finalizacion():
            ganador_declarado.wait(timeout=30)  # Timeout de seguridad
            time.sleep(0.5)  # Esperar a que se procesen últimos eventos
            with race_state['lock']:
                race_state['running'] = False
                if race_state['winner'] is None:
                    event_queue.put(('status', 'Carrera terminada (timeout)'))
        
        threading.Thread(target=monitor_finalizacion, daemon=True, name='Monitor-Carrera').start()

    # Servicios placeholders
    def servicio_pop3():
        event_queue.put(('status','POP3 placeholder (implementación futura)'))
    def servicio_smtp():
        event_queue.put(('status','SMTP placeholder (implementación futura)'))
    def servicio_ftp():
        event_queue.put(('status','FTP placeholder (implementación futura)'))

    # Seguridad avanzada
    def generar_rsa():
        def worker():
            if rsa is None:
                event_queue.put(('status','Instala cryptography para RSA'))
                return
            event_queue.put(('status','Generando claves RSA...'))
            try:
                key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
                pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
                event_queue.put(('hash', f'Llave pública RSA:\n{pub.decode()}'))
                event_queue.put(('status','RSA generado'))
            except Exception as e:
                event_queue.put(('status', f'Error RSA: {e}'))
        threading.Thread(target=worker, daemon=True).start()

    def aes_cifrar():
        texto = simpledialog.askstring('AES','Texto a cifrar')
        if not texto:
            return
        def worker():
            try:
                from cryptography.fernet import Fernet
            except ModuleNotFoundError:
                event_queue.put(('status','Instala cryptography para AES/Fernet'))
                return
            key = Fernet.generate_key(); f = Fernet(key)
            ct = f.encrypt(texto.encode())
            event_queue.put(('hash', f'AES(Fernet)\nKey: {key.decode()}\nCT: {ct.decode()}'))
            event_queue.put(('status','Texto cifrado'))
        threading.Thread(target=worker, daemon=True).start()

    # STATUS BAR
    status = tk.Frame(root, bd=1, relief="sunken")
    status.grid(row=2, column=0, columnspan=3, sticky="ew")
    status.columnconfigure(0, weight=1)
    status.columnconfigure(1, weight=1)
    status.columnconfigure(2, weight=1)
    status.columnconfigure(3, weight=1)
    status.columnconfigure(4, weight=1)

    lbl_mail = tk.Label(status, text="Correos sin leer", anchor="w", padx=6)
    lbl_temp = tk.Label(status, text="Temperatura local", anchor="w")
    lbl_net = tk.Label(status, text="Net 0 KB/s in / 0 KB/s out", anchor="w")
    lbl_dt = tk.Label(status, text="Fecha Día y Hora", anchor="e")
    lbl_alarm = tk.Label(status, text='Alarma: --', anchor='w')

    lbl_mail.grid(row=0, column=0, sticky="w")
    lbl_temp.grid(row=0, column=1, sticky="w")
    lbl_net.grid(row=0, column=2, sticky="w")
    lbl_dt.grid(row=0, column=3, sticky="e", padx=6)
    lbl_alarm.grid(row=0, column=4, sticky='w')

    # Hilo para actualizar la fecha/hora
    def updater(lbl):
        try:
            while True:
                now = datetime.datetime.now()
                lbl_text = f"{now.strftime('%A')}, {now.strftime('%Y-%m-%d %H:%M:%S')}"
                lbl.after(0, lbl.config, {"text": lbl_text})
                time.sleep(1)
        except tk.TclError:
            return

    th = threading.Thread(target=updater, args=(lbl_dt,), daemon=True)
    th.start()

    # Network I/O monitor (kb/s)
    def net_io_runner(lbl):
        try:
            import psutil
        except ModuleNotFoundError:
            lbl.after(0, lbl.config, {"text": "Instala psutil para monitor red (pip install psutil)"})
            return
        prev = psutil.net_io_counters()
        prev_time = time.time()
        try:
            while True:
                time.sleep(1)
                cur = psutil.net_io_counters()
                now = time.time()
                dt = now - prev_time if now - prev_time > 0 else 1
                sent_b = cur.bytes_sent - prev.bytes_sent
                recv_b = cur.bytes_recv - prev.bytes_recv
                sent_k = sent_b / 1024.0 / dt
                recv_k = recv_b / 1024.0 / dt
                prev = cur
                prev_time = now
                lbl_text = f"Net {recv_k:.1f} KB/s in / {sent_k:.1f} KB/s out"
                lbl.after(0, lbl.config, {"text": lbl_text})
        except tk.TclError:
            return

    threading.Thread(target=net_io_runner, args=(lbl_net,), daemon=True).start()

    # Consumir API REST con detalles mejorados
    def consumir_api(url='https://datatracker.ietf.org/doc/html/rfc6749'):
        def worker():
            event_queue.put(('status', f'GET {url}'))
            try:
                import requests
                from bs4 import BeautifulSoup
                r = requests.get(url, timeout=10)
                
                # Construir respuesta detallada
                output = []
                output.append("="*80)
                output.append(f"URL: {url}")
                output.append(f"Status: {r.status_code} {r.reason}")
                output.append(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
                output.append(f"Content-Length: {r.headers.get('Content-Length', 'N/A')}")
                output.append(f"Server: {r.headers.get('Server', 'N/A')}")
                output.append("="*80)
                output.append("\nHEADERS:")
                for k, v in list(r.headers.items())[:10]:
                    output.append(f"  {k}: {v}")
                output.append("\n" + "="*80)
                output.append("RESPONSE BODY:\n")
                
                # Intentar formatear según tipo de contenido
                content_type = r.headers.get('Content-Type', '').lower()
                
                if 'application/json' in content_type:
                    try:
                        data = r.json()
                        if isinstance(data, list):
                            output.append(f"Array with {len(data)} elements:\n")
                            output.append(json.dumps(data[:5], indent=2))  # Primeros 5 elementos
                            if len(data) > 5:
                                output.append(f"\n... and {len(data) - 5} more items")
                        else:
                            output.append(json.dumps(data, indent=2)[:3000])
                    except Exception as e:
                        output.append(f"JSON parse error: {e}\n{r.text[:2000]}")
                
                elif 'text/html' in content_type:
                    try:
                        soup = BeautifulSoup(r.text, 'html.parser')
                        # Extraer título
                        title = soup.find('title')
                        if title:
                            output.append(f"Title: {title.get_text()}\n")
                        # Extraer primeros párrafos
                        paragraphs = soup.find_all('p')[:5]
                        for p in paragraphs:
                            text = p.get_text().strip()
                            if text:
                                output.append(f"{text}\n")
                        output.append(f"\n[HTML document with {len(soup.find_all())} tags]")
                    except Exception:
                        output.append(r.text[:2000])
                
                else:
                    # Texto plano u otro
                    output.append(r.text[:3000])
                
                texto = '\n'.join(output)
                event_queue.put(('api', texto))
                event_queue.put(('status', f'✓ Respuesta {r.status_code} - {len(r.content)} bytes'))
            except Exception as e:
                event_queue.put(('api', f'ERROR: {str(e)}'))
                event_queue.put(('status', f'✗ Error API: {e}'))
        threading.Thread(target=worker, daemon=True).start()

    # Añadir botón API en pestaña Navegador después de crear pestañas (modificar contenido)

    # Pump de cola
    def pump_queue():
        try:
            while True:
                tipo, payload = event_queue.get_nowait()
                if tipo == 'status':
                    info_label.config(text=payload)
                elif tipo == 'scrape':
                    tab_texts['Resultados'].insert('end', payload + '\n---\n')
                elif tipo == 'hash':
                    tab_texts['Resultados'].insert('end', payload + '\n')
                elif tipo == 'chat':
                    tab_texts['Resultados'].insert('end', f'[CHAT] {payload}\n')
                elif tipo == 'alarm_progress':
                    lbl_alarm.config(text=f'Alarma: {payload}s')
                elif tipo == 'alarm':
                    lbl_alarm.config(text='Alarma disparada')
                    messagebox.showinfo('Alarma', '¡Tiempo cumplido!')
                elif tipo == 'api':
                    tab_texts['Navegador'].insert('end', payload + '\n')
                elif tipo == 'race_start':
                    num_corredores = payload
                    tab_texts['Tareas'].delete('1.0', 'end')
                    # Crear tags con colores para cada camello
                    colores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
                    for i in range(num_corredores):
                        tab_texts['Tareas'].tag_config(f'camello_{i}', foreground=colores[i % len(colores)], font=('Courier', 10, 'bold'))
                    tab_texts['Tareas'].insert('end', f'🏁 CARRERA INICIADA - {num_corredores} camellos 🏁\n', 'title')
                    tab_texts['Tareas'].insert('end', '='*60 + '\n\n')
                    for i in range(num_corredores):
                        tab_texts['Tareas'].insert('end', f'Camello {i+1}: [░'*40 + f'] 0/{num_corredores*10}\n', f'camello_{i}')
                elif tipo == 'race_update':
                    idx, pos, meta = payload
                    progreso = int((pos / meta) * 40)
                    barra = '█' * progreso + '░' * (40 - progreso)
                    line_num = idx + 4
                    try:
                        inicio = tab_texts['Tareas'].index(f'{line_num}.0')
                        fin = tab_texts['Tareas'].index(f'{line_num}.end')
                        tab_texts['Tareas'].delete(inicio, fin)
                        nueva_linea = f'Camello {idx+1}: [{barra}] {pos}/{meta}'
                        tab_texts['Tareas'].insert(inicio, nueva_linea, f'camello_{idx}')
                    except:
                        pass
                elif tipo == 'race_end':
                    g = payload
                    tab_texts['Tareas'].insert('end', '\n' + '='*60 + '\n')
                    tab_texts['Tareas'].insert('end', f'🏆 ¡GANADOR: CAMELLO {g+1}! 🏆\n')
                    tab_texts['Tareas'].insert('end', '='*60 + '\n')
                    event_queue.put(('status', f'Carrera finalizada - Ganó Camello {g+1}'))
                elif tipo == 'scrape_result':
                    tab_texts['Navegador'].delete('1.0', 'end')
                    tab_texts['Navegador'].insert('end', payload)
        except queue.Empty:
            pass
        root.after(200, pump_queue)
    root.after(200, pump_queue)

    root.mainloop()


if __name__ == '__main__':
    start_client()
import socket
import threading
import json

class ChatServer:
    def __init__(self, host='0.0.0.0', port=3333):
        self.host = host
        self.port = port
        self.clients = []  # [{'socket':..., 'address':..., 'username':...}]
        self.server = None

    def start(self):
        import random
        import time
        max_attempts = 10
        attempt = 0
        port_ok = False
        while attempt < max_attempts:
            try:
                self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server.bind((self.host, self.port))
                port_ok = True
                break
            except OSError as e:
                print(f"[ERROR] Puerto {self.port} ocupado. Intentando otro...")
                self.port = random.randint(20000, 60000)
                attempt += 1
                time.sleep(0.5)
        if not port_ok:
            while True:
                try:
                    user_port = input("Introduce un puerto libre para el servidor: ")
                    self.port = int(user_port)
                    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.server.bind((self.host, self.port))
                    break
                except Exception as e:
                    print(f"[ERROR] No se pudo usar el puerto {self.port}: {e}")
        self.server.listen(5)
        print(f"[INICIO] Servidor escuchando en {self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server.accept()
            t = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            t.start()

    def broadcast(self, message, exclude_socket=None):
        for client in self.clients:
            if client['socket'] != exclude_socket:
                try:
                    client['socket'].send(message)
                except:
                    try:
                        client['socket'].close()
                    except:
                        pass
                    self.clients.remove(client)

    def send_user_list(self):
        user_list = [c['username'] for c in self.clients if c.get('username')]
        data = {'type': 'user_list', 'users': user_list}
        msg = json.dumps(data).encode('utf-8')
        for client in self.clients:
            try:
                client['socket'].send(msg)
            except:
                pass

    def handle_client(self, client_socket, client_address):
        print(f"[NUEVO CLIENTE] {client_address} conectado.")
        username = None
        try:
            data = client_socket.recv(1024)
            if not data:
                client_socket.close()
                return
            try:
                msg = data.decode('utf-8')
                if msg.startswith('{'):
                    obj = json.loads(msg)
                    if obj.get('type') == 'login' and obj.get('username'):
                        username = obj['username']
            except Exception:
                pass
            if not username:
                client_socket.send(b'Usuario no proporcionado. Desconectando.')
                client_socket.close()
                return
            # Comprobar si el nombre solo contiene letras del abecedario inglés
            # Limpiar espacios y asegurar tipo string
            if not isinstance(username, str):
                client_socket.send(b'Nombre de usuario invalido. Solo letras A-Z permitidas. Desconectando.')
                client_socket.close()
                return
            username = username.strip()
            # Permitir solo letras y espacios
            if not username or not username.isascii() or not all(c.isalpha() or c == ' ' for c in username):
                client_socket.send(b'Nombre de usuario invalido. Solo letras A-Z y espacios permitidos. Desconectando.')
                client_socket.close()
                return
            # Comprobar si el nombre ya está en uso
            if any(c['username'] == username for c in self.clients):
                client_socket.send(b'Nombre de usuario en uso. Desconectando.')
                client_socket.close()
                return
            client_info = {'socket': client_socket, 'address': client_address, 'username': username}
            self.clients.append(client_info)
            print(f"[LOGIN] {username} desde {client_address}")
            self.send_user_list()
            while True:
                message = client_socket.recv(1024)
                if not message:
                    break
                try:
                    msg = message.decode('utf-8')
                    if msg.startswith('{'):
                        obj = json.loads(msg)
                        if obj.get('type') == 'msg':
                            texto = obj.get('text', '')
                            remitente = obj.get('from', username)
                            para = obj.get('to')
                            if para:
                                # Mensaje privado
                                for c in self.clients:
                                    if c['username'] == para or (isinstance(para, list) and c['username'] in para):
                                        try:
                                            privado = obj.copy()
                                            privado['private'] = True
                                            c['socket'].send(json.dumps(privado).encode('utf-8'))
                                        except:
                                            pass
                                # También enviar copia al remitente
                                for c in self.clients:
                                    if c['username'] == remitente:
                                        try:
                                            privado = obj.copy()
                                            privado['private'] = True
                                            c['socket'].send(json.dumps(privado).encode('utf-8'))
                                        except:
                                            pass
                            else:
                                obj['private'] = False
                                # Enviar a todos, incluido el remitente
                                self.broadcast(json.dumps(obj).encode('utf-8'), exclude_socket=None)
                    else:
                        # Mensaje no JSON, reenviar a todos, incluido el remitente
                        self.broadcast(message, exclude_socket=None)
                except Exception as e:
                    print(f"[ERROR] {e}")
        except Exception as e:
            print(f"[DESCONECTADO] {client_address} se ha desconectado. Error: {e}")
        finally:
            for c in self.clients[:]:
                if c['socket'] == client_socket:
                    self.clients.remove(c)
            client_socket.close()
            self.send_user_list()

if __name__ == "__main__":
    ChatServer().start()

import socket
import threading

# Configuraci  n del servidor
HOST = '0.0.0.0'  # Escucha en todas las interfaces de red
PORT = 3333       # Puerto de escucha
clients = []      # Lista para almacenar los clientes conectados

# Funci  n para retransmitir mensajes a todos los clientes
def broadcast(message, client_socket):
    for client in clients:
        if client != client_socket:  # Evitar enviar el mensaje al remitente
            try:
                client.send(message)
            except:
                # Si falla el env  o, eliminar el cliente
                clients.remove(client)

# Función para manejar la comunicación con un cliente
def handle_client(client_socket, client_address):
    print(f"[NUEVO CLIENTE] {client_address} conectado.")
    while True:
        try:
            # Recibir mensaje del cliente
            message = client_socket.recv(1024)
            if not message:
                break  # Si no hay mensaje, el cliente cerr   la conexi  n
            print(f"[{client_address}] {message.decode('utf-8')}")
            # Retransmitir el mensaje a los dem  s clientes
            broadcast(message, client_socket)
        except:
            print(f"[DESCONECTADO] {client_address} se ha desconectado.")
            clients.remove(client_socket)
            client_socket.close()
            break

# Funci  n principal para iniciar el servidor
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4, TCP
    server.bind((HOST, PORT))
    server.listen(5)  # M  ximo 5 conexiones en cola
    print(f"[INICIO] Servidor escuchando en {HOST}:{PORT}")

    while True:
        client_socket, client_address = server.accept()  # Aceptar nueva conexión
        clients.append(client_socket)
        print(f"[CONECTADO] Nueva conexi  n desde {client_address}")
        # Iniciar un hilo para manejar el cliente
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

# Iniciar el servidor
if __name__ == "__main__":
    start_server()
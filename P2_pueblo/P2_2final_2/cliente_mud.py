import socket
import select
import sys
import os

ip_servidor = input("Introduce la IP del servidor MUD (pulsa Enter para localhost): ").strip()
HOST = ip_servidor if ip_servidor else '127.0.0.1'
PORT = 1234

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
    except Exception as e:
        print(f"No se pudo conectar al servidor MUD en {HOST}:{PORT}.")
        print("Asegúrate de que main_mud.py está ejecutándose.")
        sys.exit()
        
    print("Conectado al MUD. Escribe 'quit' para salir.")
    
    while True:
        # Usamos select para leer del socket y del stdin (teclado) simultáneamente
        if os.name == 'nt':
            # En Windows select() no funciona con sys.stdin, así que hacemos polling con msvcrt
            import msvcrt
            
            # Comprobar si hay datos del socket
            rlist, _, _ = select.select([s], [], [], 0.1)
            if rlist:
                try:
                    data = s.recv(4096)
                    if not data:
                        print("\nDesconectado del servidor.")
                        sys.exit()
                    texto = data.decode('utf-8', errors='ignore')
                    for linea in texto.splitlines():
                        if "MUD_" not in linea:
                            print(linea)
                except socket.error:
                    print("\nError de conexión.")
                    sys.exit()
            
            # Comprobar si hay entrada de teclado (Windows)
            if msvcrt.kbhit():
                # Leer la línea entera
                msg = sys.stdin.readline()
                if msg.strip().lower() == 'quit':
                    break
                s.sendall(msg.encode('utf-8'))
        else:
            # En Linux/Mac podemos usar select para ambos
            rlist, _, _ = select.select([sys.stdin, s], [], [])
            
            for sock in rlist:
                if sock == s:
                    data = s.recv(4096)
                    if not data:
                        print("\nDesconectado del servidor.")
                        sys.exit()
                    texto = data.decode('utf-8', errors='ignore')
                    for linea in texto.splitlines():
                        if "MUD_" not in linea:
                            print(linea)
                else:
                    msg = sys.stdin.readline()
                    if msg.strip().lower() == 'quit':
                        s.close()
                        sys.exit()
                    s.sendall(msg.encode('utf-8'))

if __name__ == "__main__":
    main()

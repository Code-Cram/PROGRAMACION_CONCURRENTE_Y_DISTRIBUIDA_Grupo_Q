import socket
import select
import uuid
import sys

class MudServer:
    def __init__(self, port=1234):
        self.port = port
        self.clients = {}  # Map of client ID to socket
        self.buffers = {}  # Map of client ID to input buffer
        self.new_players = []
        self.disconnected_players = []
        self.commands = []

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(10)

    def update(self):
        """Processes network events, connections, and reads commands."""
        # Check for new connections
        rlist, _, _ = select.select([self.server_socket] + list(self.clients.values()), [], [], 0.05)
        
        for sock in rlist:
            if sock is self.server_socket:
                client_sock, addr = self.server_socket.accept()
                client_sock.setblocking(False)
                client_id = str(uuid.uuid4())
                self.clients[client_id] = client_sock
                self.buffers[client_id] = ""
                self.new_players.append(client_id)
            else:
                # Find which client this socket belongs to
                client_id = None
                for cid, csock in self.clients.items():
                    if csock is sock:
                        client_id = cid
                        break
                
                if client_id is not None:
                    try:
                        data = sock.recv(1024)
                        if data:
                            try:
                                decoded_data = data.decode('utf-8')
                            except UnicodeDecodeError:
                                decoded_data = data.decode('latin1', errors='ignore')
                            
                            self.buffers[client_id] += decoded_data
                            
                            while '\n' in self.buffers[client_id]:
                                line, self.buffers[client_id] = self.buffers[client_id].split('\n', 1)
                                line = line.strip()
                                if line:
                                    parts = line.split(' ', 1)
                                    command = parts[0]
                                    params = parts[1] if len(parts) > 1 else ""
                                    self.commands.append((client_id, command, params))
                        else:
                            # Empty data means disconnected
                            self._disconnect(client_id)
                    except socket.error:
                        self._disconnect(client_id)

    def _disconnect(self, client_id):
        if client_id in self.clients:
            sock = self.clients[client_id]
            try:
                sock.close()
            except Exception:
                pass
            del self.clients[client_id]
            del self.buffers[client_id]
            self.disconnected_players.append(client_id)

    def disconnect_player(self, client_id):
        self._disconnect(client_id)

    def send_message(self, client_id, message):
        """Sends a message to a specific client."""
        if client_id in self.clients:
            try:
                self.clients[client_id].sendall((message + "\n").encode('utf-8'))
            except socket.error:
                self._disconnect(client_id)

    def get_new_players(self):
        """Returns a list of new player IDs and clears the queue."""
        players = self.new_players[:]
        self.new_players.clear()
        return players

    def get_disconnected_players(self):
        """Returns a list of disconnected player IDs and clears the queue."""
        players = self.disconnected_players[:]
        self.disconnected_players.clear()
        return players

    def get_commands(self):
        """Returns a list of tuples (player_id, command, params) and clears the queue."""
        cmds = self.commands[:]
        self.commands.clear()
        return cmds

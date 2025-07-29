from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import os
import random
import string
import sqlite3

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import os
import random
import string
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, async_mode='eventlet')

# In-memory structures for servers, channels, and user presence
servers = {
    'General': {
        'channels': ['general', 'random'],
        'users': set()
    }
}
user_sessions = {}  # sid -> {'username': ..., 'avatar': ..., 'server': ..., 'channel': ...}
avatars = [
    '🐱', '🐶', '🦊', '🐻', '🐼', '🐸', '🦁', '🐵', '🐧', '🐤', '🐯', '🦄', '🐙', '🐢', '🐝', '🐞', '🦋', '🐬', '🐳', '🦕'
]

def random_username():
    return 'Anon' + ''.join(random.choices(string.digits, k=4))

def random_avatar():
    return random.choice(avatars)

def init_db():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        server_id INTEGER NOT NULL,
        FOREIGN KEY(server_id) REFERENCES servers(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        avatar TEXT NOT NULL,
        text TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(server_id) REFERENCES servers(id),
        FOREIGN KEY(channel_id) REFERENCES channels(id)
    )''')
    # Drop and recreate users table to fix schema
    c.execute('DROP TABLE IF EXISTS users')
    c.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        avatar TEXT NOT NULL,
        status TEXT DEFAULT '',
        session_id TEXT UNIQUE,
        online INTEGER DEFAULT 0,
        last_seen DATETIME
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        emoji TEXT NOT NULL,
        username TEXT NOT NULL,
        avatar TEXT NOT NULL,
        UNIQUE(message_id, emoji, username, avatar),
        FOREIGN KEY(message_id) REFERENCES messages(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pinned_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        server_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        pinned_by TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(message_id, channel_id),
        FOREIGN KEY(message_id) REFERENCES messages(id)
    )''')
    conn.commit()
    conn.close()

def load_servers_channels():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM servers')
    servers_db = c.fetchall()
    servers.clear()
    for server_id, server_name in servers_db:
        c.execute('SELECT name FROM channels WHERE server_id=?', (server_id,))
        channels = [row[0] for row in c.fetchall()]
        servers[server_name] = {'id': server_id, 'channels': channels, 'users': set()}
    conn.close()

# Call on startup
init_db()
load_servers_channels()

@app.route('/')
def index():
    return render_template('index.html', servers=servers)

# Socket.IO events
# On connect, set online=1 and update last_seen
@socketio.on('connect')
def handle_connect(auth):
    print(f"[DEBUG] New client connected: {request.sid}")
    sid = request.sid
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT username, avatar, status FROM users WHERE session_id=?', (sid,))
    row = c.fetchone()
    if row:
        username, avatar, status = row
        c.execute('UPDATE users SET online=1, last_seen=datetime("now") WHERE session_id=?', (sid,))
    else:
        username = random_username()
        avatar = random_avatar()
        status = ''
        c.execute('INSERT INTO users (username, avatar, status, session_id, online, last_seen) VALUES (?, ?, ?, ?, 1, datetime("now"))', (username, avatar, status, sid))
    conn.commit()
    conn.close()
    user_sessions[sid] = {'username': username, 'avatar': avatar, 'status': status, 'server': None, 'channel': None}
    print(f"[DEBUG] User session created: {user_sessions[sid]}")
    emit('session', {'username': username, 'avatar': avatar, 'status': status})
    emit('server_list', {'servers': list(servers.keys())}, to=request.sid)

@socketio.on('update_profile')
def handle_update_profile(data):
    sid = request.sid
    username = data.get('username')
    avatar = data.get('avatar')
    status = data.get('status')
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('UPDATE users SET username=?, avatar=?, status=? WHERE session_id=?', (username, avatar, status, sid))
    conn.commit()
    conn.close()
    # Update in-memory session
    user_sessions[sid]['username'] = username
    user_sessions[sid]['avatar'] = avatar
    user_sessions[sid]['status'] = status
    emit('profile_updated', {'username': username, 'avatar': avatar, 'status': status})

@socketio.on('create_server')
def handle_create_server(data):
    print("Received create_server event with data:", data, flush=True)
    server_name = data['server']
    if server_name not in servers:
        print(f"Adding server: {server_name}", flush=True)
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        c.execute('INSERT INTO servers (name) VALUES (?)', (server_name,))
        server_id = c.lastrowid
        c.execute('INSERT INTO channels (name, server_id) VALUES (?, ?)', ('general', server_id))
        conn.commit()
        conn.close()
        servers[server_name] = {'id': server_id, 'channels': ['general'], 'users': set()}
        emit('server_list', {'servers': list(servers.keys())}, broadcast=True)
    else:
        print(f"Server {server_name} already exists", flush=True)

@socketio.on('join_server')
def handle_join_server(data):
    sid = request.sid
    server = data['server']
    print(f"[DEBUG] join_server event: sid={sid}, server={server}", flush=True)
    if server in servers:
        user_sessions[sid]['server'] = server
        user_sessions[sid]['channel'] = servers[server]['channels'][0]
        servers[server]['users'].add(sid)
        emit('channel_list', {'channels': servers[server]['channels']})
        update_user_list(server)

@socketio.on('create_channel')
def handle_create_channel(data):
    print("Received create_channel event with data:", data, flush=True)
    server = data['server']
    channel = data['channel']
    if server in servers and channel not in servers[server]['channels']:
        print(f"Adding channel '{channel}' to server '{server}'", flush=True)
        server_id = servers[server]['id']
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        c.execute('INSERT INTO channels (name, server_id) VALUES (?, ?)', (channel, server_id))
        conn.commit()
        conn.close()
        servers[server]['channels'].append(channel)
        emit('channel_list', {'channels': servers[server]['channels']}, broadcast=True)
    else:
        print(f"Channel '{channel}' already exists in server '{server}' or server not found.", flush=True)

@socketio.on('join_channel')
def handle_join_channel(data):
    sid = request.sid
    server = data['server']
    channel = data['channel']
    print(f"[DEBUG] join_channel event: sid={sid}, server={server}, channel={channel}", flush=True)
    if server in servers and channel in servers[server]['channels']:
        prev_channel = user_sessions[sid]['channel']
        if prev_channel:
            leave_room(f'{server}:{prev_channel}')
        user_sessions[sid]['channel'] = channel
        join_room(f'{server}:{channel}')
        emit('joined_channel', {'channel': channel})
        # Load last 50 messages from DB
        server_id = servers[server]['id']
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        c.execute('SELECT id FROM channels WHERE name=? AND server_id=?', (channel, server_id))
        row = c.fetchone()
        if row:
            channel_id = row[0]
            c.execute('SELECT id, username, avatar, text, timestamp FROM messages WHERE server_id=? AND channel_id=? ORDER BY id DESC LIMIT 50', (server_id, channel_id))
            messages = c.fetchall()[::-1]  # reverse to chronological order
            for msg_id, username, avatar, text, timestamp in messages:
                # Lookup status for each user
                c2 = conn.cursor()
                c2.execute('SELECT status FROM users WHERE username=? AND avatar=?', (username, avatar))
                status_row = c2.fetchone()
                status = status_row[0] if status_row else ''
                # Get reactions
                c2.execute('SELECT emoji, username, avatar FROM reactions WHERE message_id=?', (msg_id,))
                rows = c2.fetchall()
                reactions = {}
                for emoji, uname, av in rows:
                    if emoji not in reactions:
                        reactions[emoji] = []
                    reactions[emoji].append({'username': uname, 'avatar': av})
                emit('message', {'msg': text, 'username': username, 'avatar': avatar, 'id': msg_id, 'timestamp': timestamp, 'status': status, 'reactions': reactions})
        conn.close()
        update_user_list(server)
        broadcast_pinned_messages(server, channel)

@socketio.on('edit_message')
def handle_edit_message(data):
    msg_id = data['id']
    new_text = data['text']
    sid = request.sid
    username = user_sessions[sid]['username']
    avatar = user_sessions[sid]['avatar']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    # Only allow editing if the message belongs to the user
    c.execute('SELECT username, avatar FROM messages WHERE id=?', (msg_id,))
    row = c.fetchone()
    if row and row[0] == username and row[1] == avatar:
        c.execute('UPDATE messages SET text=? WHERE id=?', (new_text, msg_id))
        conn.commit()
        # Fetch updated message details to emit
        c.execute('SELECT server_id, channel_id, username, avatar, text, timestamp FROM messages WHERE id=?', (msg_id,))
        updated_msg = c.fetchone()
        if updated_msg:
            server_id, channel_id, username, avatar, text, timestamp = updated_msg
            # Get server and channel names
            c.execute('SELECT name FROM servers WHERE id=?', (server_id,))
            server_row = c.fetchone()
            server_name = server_row[0] if server_row else ''
            c.execute('SELECT name FROM channels WHERE id=?', (channel_id,))
            channel_row = c.fetchone()
            channel_name = channel_row[0] if channel_row else ''
            # Get reactions
            c.execute('SELECT emoji, username, avatar FROM reactions WHERE message_id=?', (msg_id,))
            rows = c.fetchall()
            reactions = {}
            for emoji, uname, av in rows:
                if emoji not in reactions:
                    reactions[emoji] = []
                reactions[emoji].append({'username': uname, 'avatar': av})
            socketio.emit('message_update', {
                'id': msg_id,
                'server': server_name,
                'channel': channel_name,
                'username': username,
                'avatar': avatar,
                'msg': text,
                'timestamp': timestamp,
                'reactions': reactions
            }, broadcast=True, namespace='/')
    conn.close()

@socketio.on('delete_message')
def handle_delete_message(data):
    msg_id = data['id']
    sid = request.sid
    username = user_sessions[sid]['username']
    avatar = user_sessions[sid]['avatar']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    # Only allow deleting if the message belongs to the user
    c.execute('SELECT username, avatar FROM messages WHERE id=?', (msg_id,))
    row = c.fetchone()
    if row and row[0] == username and row[1] == avatar:
        c.execute('DELETE FROM messages WHERE id=?', (msg_id,))
        conn.commit()
        # Emit message_update with msg set to None to indicate deletion
        socketio.emit('message_update', {'id': msg_id, 'msg': None}, broadcast=True, namespace='/')
    conn.close()

# Update message sending to include id and timestamp
@socketio.on('message')
def handle_message(data, ack=None):
    temp_id = data.get('tempId')  # Receive tempId from client

    sid = request.sid
    server = user_sessions[sid]['server']
    channel = user_sessions[sid]['channel']
    msg = data['msg']
    username = user_sessions[sid]['username']
    avatar = user_sessions[sid]['avatar']
    status = user_sessions[sid].get('status', '')
    print(f"[DEBUG] message event: sid={sid}, server={server}, channel={channel}, msg={msg}", flush=True)
    if server and channel:
        print(f"[DEBUG] Saving message to DB: {msg}", flush=True)
        # Save message to DB
        server_id = servers[server]['id']
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        c.execute('SELECT id FROM channels WHERE name=? AND server_id=?', (channel, server_id))
        row = c.fetchone()
        if row:
            channel_id = row[0]
            c.execute('INSERT INTO messages (server_id, channel_id, username, avatar, text) VALUES (?, ?, ?, ?, ?)',
                      (server_id, channel_id, username, avatar, msg))
            msg_id = c.lastrowid
            c.execute('SELECT timestamp FROM messages WHERE id=?', (msg_id,))
            timestamp = c.fetchone()[0]
            # Get reactions (should be empty for new message)
            c.execute('SELECT emoji, username, avatar FROM reactions WHERE message_id=?', (msg_id,))
            rows = c.fetchall()
            reactions = {}
            for emoji, uname, av in rows:
                if emoji not in reactions:
                    reactions[emoji] = []
                reactions[emoji].append({'username': uname, 'avatar': av})
            conn.commit()
            print(f"[DEBUG] Emitting message event for message id {msg_id}", flush=True)
            socketio.emit('message', {
                'msg': msg,
                'username': username,
                'avatar': avatar,
                'id': msg_id,
                'timestamp': timestamp,
                'status': status,
                'reactions': reactions,
                'tempId': temp_id  # Include it back
            }, room=f'{server}:{channel}')
        conn.close()
    if ack:
        ack()

@socketio.on('typing')
def handle_typing(data):
    sid = request.sid
    server = user_sessions[sid]['server']
    channel = user_sessions[sid]['channel']
    username = user_sessions[sid]['username']
    if server and channel:
        emit('typing', {'user': username}, room=f'{server}:{channel}', include_self=False)

@socketio.on('add_reaction')
def handle_add_reaction(data):
    msg_id = data['message_id']
    emoji = data['emoji']
    sid = request.sid
    username = user_sessions[sid]['username']
    avatar = user_sessions[sid]['avatar']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO reactions (message_id, emoji, username, avatar) VALUES (?, ?, ?, ?)', (msg_id, emoji, username, avatar))
    conn.commit()
    conn.close()
    broadcast_reactions(msg_id)

@socketio.on('remove_reaction')
def handle_remove_reaction(data):
    msg_id = data['message_id']
    emoji = data['emoji']
    sid = request.sid
    username = user_sessions[sid]['username']
    avatar = user_sessions[sid]['avatar']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('DELETE FROM reactions WHERE message_id=? AND emoji=? AND username=? AND avatar=?', (msg_id, emoji, username, avatar))
    conn.commit()
    conn.close()
    broadcast_reactions(msg_id)

def broadcast_reactions(msg_id):
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT emoji, username, avatar FROM reactions WHERE message_id=?', (msg_id,))
    rows = c.fetchall()
    conn.close()
    # Group by emoji: {emoji: [user, ...]}
    reactions = {}
    for emoji, username, avatar in rows:
        if emoji not in reactions:
            reactions[emoji] = []
        reactions[emoji].append({'username': username, 'avatar': avatar})
    socketio.emit('reactions_update', {'message_id': msg_id, 'reactions': reactions}, broadcast=True, namespace='/')

@socketio.on('pin_message')
def handle_pin_message(data):
    msg_id = data['message_id']
    sid = request.sid
    username = user_sessions[sid]['username']
    server = user_sessions[sid]['server']
    channel = user_sessions[sid]['channel']
    if not (server and channel):
        return
    server_id = servers[server]['id']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT id FROM channels WHERE name=? AND server_id=?', (channel, server_id))
    row = c.fetchone()
    if row:
        channel_id = row[0]
        c.execute('INSERT OR IGNORE INTO pinned_messages (message_id, server_id, channel_id, pinned_by) VALUES (?, ?, ?, ?)', (msg_id, server_id, channel_id, username))
        conn.commit()
    conn.close()
    broadcast_pinned_messages(server, channel)

@socketio.on('unpin_message')
def handle_unpin_message(data):
    msg_id = data['message_id']
    sid = request.sid
    server = user_sessions[sid]['server']
    channel = user_sessions[sid]['channel']
    if not (server and channel):
        return
    server_id = servers[server]['id']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT id FROM channels WHERE name=? AND server_id=?', (channel, server_id))
    row = c.fetchone()
    if row:
        channel_id = row[0]
        c.execute('DELETE FROM pinned_messages WHERE message_id=? AND channel_id=?', (msg_id, channel_id))
        conn.commit()
    conn.close()
    broadcast_pinned_messages(server, channel)

def broadcast_pinned_messages(server, channel):
    server_id = servers[server]['id']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT id FROM channels WHERE name=? AND server_id=?', (channel, server_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    channel_id = row[0]
    c.execute('''SELECT m.id, m.username, m.avatar, m.text, m.timestamp FROM pinned_messages p
                 JOIN messages m ON p.message_id = m.id
                 WHERE p.channel_id=? ORDER BY p.timestamp DESC''', (channel_id,))
    pinned = c.fetchall()
    conn.close()
    socketio.emit('pinned_messages', {'server': server, 'channel': channel, 'messages': [
        {'id': msg_id, 'username': username, 'avatar': avatar, 'text': text, 'timestamp': timestamp}
        for msg_id, username, avatar, text, timestamp in pinned
    ]}, room=f'{server}:{channel}')


# On disconnect, set online=0 and update last_seen
@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"[DEBUG] Client disconnected: {sid}")
    user = user_sessions.get(sid)
    if user:
        server = user['server']
        if server and server in servers and sid in servers[server]['users']:
            servers[server]['users'].remove(sid)
            update_user_list(server)
        del user_sessions[sid]
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('UPDATE users SET online=0, last_seen=datetime("now") WHERE session_id=?', (sid,))
    conn.commit()
    conn.close()

def update_user_list(server):
    user_list = []
    for sid in servers[server]['users']:
        if sid in user_sessions:
            username = user_sessions[sid]['username']
            avatar = user_sessions[sid]['avatar']
            status = user_sessions[sid].get('status', '')
            conn = sqlite3.connect('chat.db')
            c = conn.cursor()
            c.execute('SELECT online, last_seen FROM users WHERE username=? AND avatar=?', (username, avatar))
            row = c.fetchone()
            online = bool(row[0]) if row else False
            last_seen = row[1] if row else ''
            conn.close()
            user_list.append({'username': username, 'avatar': avatar, 'status': status, 'online': online, 'last_seen': last_seen})
    for sid in servers[server]['users']:
        if sid in user_sessions:
            channel = user_sessions[sid].get('channel')
            if channel:
                emit('user_list', {'users': user_list}, room=f'{server}:{channel}')

@socketio.on('get_server_list')
def handle_get_server_list():
    emit('server_list', {'servers': list(servers.keys())}, broadcast=True)

@socketio.on('delete_server')
def handle_delete_server(data):
    server_name = data.get('server')
    print(f"Deleting server: {server_name}")  # Debug

    if server_name in servers:
        # Remove from in-memory servers dictionary
        servers.pop(server_name)

        # Remove from database
        conn = sqlite3.connect('chat.db')
        c = conn.cursor()
        # Get server id
        c.execute('SELECT id FROM servers WHERE name=?', (server_name,))
        row = c.fetchone()
        if row:
            server_id = row[0]
            # Delete channels for this server
            c.execute('DELETE FROM channels WHERE server_id=?', (server_id,))
            # Delete messages for this server
            c.execute('DELETE FROM messages WHERE server_id=?', (server_id,))
            # Delete pinned messages for this server
            c.execute('DELETE FROM pinned_messages WHERE server_id=?', (server_id,))
            # Delete the server itself
            c.execute('DELETE FROM servers WHERE id=?', (server_id,))
            conn.commit()
        conn.close()

        # Emit update to all clients
        emit('server_deleted', {'server': server_name}, broadcast=True)

@socketio.on('clear_chat')
def handle_clear_chat():
    sid = request.sid
    user = user_sessions.get(sid)
    if not user:
        return
    server = user.get('server')
    channel = user.get('channel')
    if not server or not channel:
        return
    server_id = servers[server]['id']
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('SELECT id FROM channels WHERE name=? AND server_id=?', (channel, server_id))
    row = c.fetchone()
    if row:
        channel_id = row[0]
        # Delete all messages for this server and channel
        c.execute('DELETE FROM messages WHERE server_id=? AND channel_id=?', (server_id, channel_id))
        conn.commit()
        # Emit event to clear chat for all clients in the room
        socketio.emit('chat_cleared', room=f'{server}:{channel}')
    conn.close()

if __name__ == '__main__':
    socketio.run(app, debug=True)

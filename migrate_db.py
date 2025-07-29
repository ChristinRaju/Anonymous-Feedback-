import sqlite3

def migrate_add_user_session_id():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('PRAGMA foreign_keys=off;')
    c.execute('BEGIN TRANSACTION;')
    # Rename old table
    c.execute('ALTER TABLE messages RENAME TO old_messages;')
    # Create new messages table with user_session_id
    c.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            avatar TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_session_id TEXT,
            FOREIGN KEY(server_id) REFERENCES servers(id),
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        );
    ''')
    # Copy data from old_messages to messages, set user_session_id to NULL for now
    c.execute('''
        INSERT INTO messages (id, server_id, channel_id, username, avatar, text, timestamp)
        SELECT id, server_id, channel_id, username, avatar, text, timestamp FROM old_messages;
    ''')
    c.execute('DROP TABLE old_messages;')
    c.execute('COMMIT;')
    c.execute('PRAGMA foreign_keys=on;')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate_add_user_session_id()

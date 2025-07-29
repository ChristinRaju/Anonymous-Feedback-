import sqlite3

def print_messages_table_schema():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(messages)")
    columns = c.fetchall()
    print("Schema of 'messages' table:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    print_messages_table_schema()

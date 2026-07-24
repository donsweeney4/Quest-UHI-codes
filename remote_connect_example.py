import os
import mysql.connector
from mysql.connector import Error


def connect_to_database():
    """Connect to the UHI MySQL database from a remote host.

    Expects these environment variables to be set (values provided
    separately, e.g. DB_HOST=100.20.98.153):
        DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    """
    try:
        connection = mysql.connector.connect(
            host=os.environ['DB_HOST'],
            port=int(os.environ.get('DB_PORT', 3306)),
            database=os.environ.get('DB_NAME', 'uhi'),
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
        )
        if connection.is_connected():
            print("Connected to MySQL database")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


if __name__ == '__main__':
    conn = connect_to_database()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        print("MySQL version:", cursor.fetchone()[0])
        cursor.close()
        conn.close()

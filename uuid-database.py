#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "cryptography",
# ]
# ///

import os
import base64
import argparse
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib
import sqlite3

# Configuration
SECRET_KEY = "your-secret-here"  # Keep this secret!

# Database setup
DB_FILE = "items.db"


def setup_database():
    """Create the database and table if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()


# Utility functions for ID encoding/decoding
def encode_id(id_value):
    # Convert ID to string and pad to ensure consistent length
    text = str(id_value).zfill(10).encode('utf-8')

    # Create key from secret
    key = hashlib.sha256(SECRET_KEY.encode()).digest()

    # Generate random IV
    iv = os.urandom(16)

    # Create cipher
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Encrypt the ID
    encrypted = encryptor.update(text) + encryptor.finalize()

    # Combine IV and encrypted data and convert to URL-safe base64
    result = base64.urlsafe_b64encode(iv + encrypted).decode('ascii')

    return result


def decode_id(hash_value):
    try:
        # Decode from URL-safe base64
        decoded = base64.urlsafe_b64decode(hash_value)

        # Extract IV and encrypted data
        iv = decoded[:16]
        encrypted = decoded[16:]

        # Create key from secret
        key = hashlib.sha256(SECRET_KEY.encode()).digest()

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt
        decrypted = decryptor.update(encrypted) + decryptor.finalize()

        # Convert to integer
        return int(decrypted.decode('utf-8'))
    except Exception as e:
        print(f"Failed to decode ID: {e}")
        return None


# Database operations
def create_item(name):
    """Create a new item and return its internal and public IDs"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('INSERT INTO items (name) VALUES (?)', (name,))
    conn.commit()

    # Get the auto-incremented ID
    internal_id = cursor.lastrowid
    conn.close()

    # Generate the public ID
    public_id = encode_id(internal_id)

    return internal_id, public_id


def get_item(public_id):
    """Get an item by its public ID"""
    # Decode the public ID to get the internal ID
    internal_id = decode_id(public_id)
    if internal_id is None:
        return None

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id, name FROM items WHERE id = ?', (internal_id,))
    item = cursor.fetchone()
    conn.close()

    return item


def list_items():
    """List all items with their internal and public IDs"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT id, name FROM items')
    items = cursor.fetchall()
    conn.close()

    result = []
    for internal_id, name in items:
        public_id = encode_id(internal_id)
        result.append((internal_id, public_id, name))

    return result


def main():
    parser = argparse.ArgumentParser(description='Item ID management system')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create item command
    create_parser = subparsers.add_parser('create', help='Create a new item')
    create_parser.add_argument('name', help='Name of the item')

    # Get item by public ID command
    get_parser = subparsers.add_parser('get', help='Get item by public ID')
    get_parser.add_argument('public_id', help='Public ID of the item')

    # List all items command
    subparsers.add_parser('list', help='List all items')

    # Encode/decode commands for testing
    encode_parser = subparsers.add_parser('encode', help='Encode an internal ID')
    encode_parser.add_argument('id', type=int, help='Internal ID to encode')

    decode_parser = subparsers.add_parser('decode', help='Decode a public ID')
    decode_parser.add_argument('public_id', help='Public ID to decode')

    args = parser.parse_args()

    # Set up the database
    setup_database()

    if args.command == 'create':
        internal_id, public_id = create_item(args.name)
        print(f"Created item: '{args.name}'")
        print(f"Internal ID: {internal_id}")
        print(f"Public ID: {public_id}")

    elif args.command == 'get':
        item = get_item(args.public_id)
        if item:
            internal_id, name = item
            print(f"Found item: '{name}'")
            print(f"Internal ID: {internal_id}")
            print(f"Public ID: {args.public_id}")
        else:
            print("Item not found or invalid public ID")

    elif args.command == 'list':
        items = list_items()
        if items:
            print("Items:")
            for internal_id, public_id, name in items:
                print(f"  - {name}")
                print(f"    Internal ID: {internal_id}")
                print(f"    Public ID: {public_id}")
        else:
            print("No items found")

    elif args.command == 'encode':
        public_id = encode_id(args.id)
        print(f"Internal ID: {args.id}")
        print(f"Encoded as: {public_id}")

    elif args.command == 'decode':
        internal_id = decode_id(args.public_id)
        if internal_id is not None:
            print(f"Public ID: {args.public_id}")
            print(f"Decoded as internal ID: {internal_id}")
        else:
            print("Failed to decode public ID")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

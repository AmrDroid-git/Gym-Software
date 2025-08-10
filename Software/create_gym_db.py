import sqlite3
import os

# --- Create folders ---
base_dir = os.path.dirname(os.path.abspath(__file__))  # current directory
faces_dir = os.path.join(base_dir, "faces")
old_faces_dir = os.path.join(faces_dir, "oldFaces")

# create folders if they don't exist
os.makedirs(old_faces_dir, exist_ok=True)

# --- Connect to SQLite (creates file if not exists) ---
conn = sqlite3.connect(os.path.join(base_dir, "gym.db"))
cursor = conn.cursor()

# Enable foreign key support
cursor.execute("PRAGMA foreign_keys = ON;")

# Create tables
cursor.executescript("""
CREATE TABLE IF NOT EXISTS Client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    id_card INTEGER UNIQUE NOT NULL,
    phone_number INTEGER,
    role TEXT CHECK(role IN ('owner', 'client', 'coach')) NOT NULL,
    picture TEXT,
    created_at DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS membership_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    months INTEGER NOT NULL CHECK(months IN (1, 3, 6, 12)),
    price_decimal INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plan_id INTEGER,  -- nullable now
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    price_paid INTEGER NOT NULL,
    FOREIGN KEY (client_id) REFERENCES Client(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES membership_plans(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    person_id INTEGER NOT NULL,
    FOREIGN KEY (person_id) REFERENCES Client(id) ON DELETE CASCADE
);
""")

# Save and close
conn.commit()
conn.close()

print("Database gym.db created successfully!")
print(f"Folders created: {faces_dir} and {old_faces_dir}")

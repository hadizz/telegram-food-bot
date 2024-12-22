import sqlite3

def init_db():
    conn = sqlite3.connect("recipes.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        ingredients TEXT NOT NULL,
        cooking_time INTEGER,
        skill_level TEXT,
        calories INTEGER,
        instructions TEXT NOT NULL,
        instruction_voice TEXT,
        image_path TEXT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        owner_id INTEGER,
        FOREIGN KEY (owner_id) REFERENCES users (telegram_id)
    )""")
    
    # Add owner_id column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE recipes ADD COLUMN owner_id INTEGER REFERENCES users(telegram_id)")
        print("Added owner_id column to recipes table")
    except sqlite3.OperationalError:
        print("owner_id column already exists")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        full_name TEXT,
        bmi FLOAT,
        preferences TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER,
        recipe_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (recipe_id) REFERENCES recipes (id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        recipe_id INTEGER,
        comment TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (recipe_id) REFERENCES recipes (id)
    )""")
    
    conn.commit()
    conn.close() 
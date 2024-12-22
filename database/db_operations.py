import sqlite3
from typing import List, Tuple, Optional

class DatabaseManager:
    def __init__(self, db_name: str = "recipes.db"):
        self.db_name = db_name
        self.SUPER_ADMIN_IDS = [123456789]  # Replace with your Telegram ID

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def save_recipe(self, recipe_data: dict, owner_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recipes (
                    title, ingredients, cooking_time, skill_level, calories, 
                    instructions, instruction_voice, image_path, created_at, updated_at,
                    owner_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)
            """, (
                recipe_data['title'],
                recipe_data['ingredients'],
                recipe_data['cooking_time'],
                recipe_data['skill_level'],
                recipe_data['calories'],
                recipe_data['instructions'],
                recipe_data.get('instruction_voice'),
                recipe_data.get('image_path'),
                owner_id
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving recipe: {e}")
            return False
        finally:
            conn.close()

    def search_recipes(self, search_term: str) -> List[Tuple]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.id, r.title, r.ingredients, r.cooking_time, r.skill_level, 
                       r.calories, r.image_path, r.owner_id, u.username
                FROM recipes r
                LEFT JOIN users u ON r.owner_id = u.telegram_id
                WHERE LOWER(r.title) LIKE ? 
                   OR LOWER(r.ingredients) LIKE ?
                   OR LOWER(r.instructions) LIKE ?
                ORDER BY r.created_at DESC
            """, (
                f'%{search_term.lower()}%',
                f'%{search_term.lower()}%',
                f'%{search_term.lower()}%'
            ))
            return cursor.fetchall()
        finally:
            conn.close()

    def save_user_bmi(self, telegram_id: int, bmi: float) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (telegram_id, bmi)
                VALUES (?, ?)
            """, (telegram_id, bmi))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving BMI: {e}")
            return False
        finally:
            conn.close()

    def get_user_bmi(self, telegram_id: int) -> Optional[float]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT bmi FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def register_user(self, telegram_id: int, username: str, full_name: str) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, full_name, is_active)
                VALUES (?, ?, ?, TRUE)
            """, (telegram_id, username, full_name))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error registering user: {e}")
            return False
        finally:
            conn.close()

    def is_user_registered(self, telegram_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT is_active FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return bool(result and result[0])
        finally:
            conn.close()

    def is_super_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.SUPER_ADMIN_IDS

    def ban_user(self, telegram_id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_active = FALSE WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_user_profile(self, telegram_id: int) -> Optional[dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, full_name, is_active, created_at
                FROM users 
                WHERE telegram_id = ?
            """, (telegram_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'username': result[0],
                    'full_name': result[1],
                    'is_active': bool(result[2]),
                    'joined_date': result[3]
                }
            return None
        finally:
            conn.close() 

    def get_user_recipes(self, telegram_id: int) -> List[Tuple]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, cooking_time, skill_level, calories, created_at
                FROM recipes
                WHERE owner_id = ?
                ORDER BY created_at DESC
            """, (telegram_id,))
            return cursor.fetchall()
        finally:
            conn.close() 

    def get_recipe_details(self, recipe_id: int) -> Optional[dict]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, ingredients, cooking_time, skill_level, calories, 
                       instructions, instruction_voice, image_path, created_at, owner_id
                FROM recipes 
                WHERE id = ?
            """, (recipe_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'title': result[0],
                    'ingredients': result[1],
                    'cooking_time': result[2],
                    'skill_level': result[3],
                    'calories': result[4],
                    'instructions': result[5],
                    'instruction_voice': result[6],
                    'image_path': result[7],
                    'created_at': result[8],
                    'owner_id': result[9]
                }
            return None
        finally:
            conn.close() 

    def update_recipe(self, recipe_id: int, telegram_id: int, recipe_data: dict) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if recipe belongs to user
            cursor.execute("""
                SELECT id FROM recipes
                WHERE id = ? AND owner_id = ?
            """, (recipe_id, telegram_id))
            
            if not cursor.fetchone():
                return False  # Recipe doesn't belong to user
            
            cursor.execute("""
                UPDATE recipes 
                SET title = ?, ingredients = ?, cooking_time = ?, 
                    skill_level = ?, calories = ?, instructions = ?,
                    instruction_voice = ?, image_path = ?, updated_at = datetime('now')
                WHERE id = ? AND owner_id = ?
            """, (
                recipe_data['title'],
                recipe_data['ingredients'],
                recipe_data['cooking_time'],
                recipe_data['skill_level'],
                recipe_data['calories'],
                recipe_data['instructions'],
                recipe_data.get('instruction_voice'),
                recipe_data.get('image_path'),
                recipe_id,
                telegram_id
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating recipe: {e}")
            return False
        finally:
            conn.close()
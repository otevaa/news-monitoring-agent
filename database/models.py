"""
Database models for NewsMonitor Pro
"""
import sqlite3
import os
import hashlib
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import json
from auth.security_manager import SecurityManager


def generate_password_hash(password: str) -> str:
    """Generate password hash using enhanced security"""
    security = SecurityManager()
    return security.hash_password(password)


def check_password_hash(stored_hash: str, password: str) -> bool:
    """Check password against stored hash"""
    security = SecurityManager()
    return security.verify_password(password, stored_hash)


class DatabaseManager:
    """Centralized database manager for all database operations"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager with flexible path configuration"""
        if db_path is None:
            # Try environment variable first
            db_path = os.getenv('DATABASE_PATH')
            
            if db_path is None:
                # Check if we're in a containerized environment (Render deployment)
                if os.path.exists('/app/db'):
                    db_path = "/app/db/newsmonitor.db"  # Persistent disk path
                else:
                    db_path = "db/newsmonitor.db"  # Local development path
        
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Get database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                email_verified INTEGER DEFAULT 0,
                verification_token TEXT,
                reset_token TEXT,
                reset_token_expires TIMESTAMP
            )
        ''')
        
        # User profiles table for AI settings and preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                ai_model TEXT DEFAULT 'openai-gpt3.5',
                ai_filtering_enabled INTEGER DEFAULT 1,
                keyword_expansion_enabled INTEGER DEFAULT 1,
                priority_alerts_enabled INTEGER DEFAULT 1,
                language TEXT DEFAULT 'fr',
                timezone TEXT DEFAULT 'Europe/Paris',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                keywords TEXT NOT NULL,
                frequency TEXT NOT NULL,
                max_articles INTEGER DEFAULT 25,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                total_articles INTEGER DEFAULT 0,
                articles_today INTEGER DEFAULT 0,
                last_articles_date TIMESTAMP,
                spreadsheet_id TEXT,
                spreadsheet_url TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Campaign integrations table (many-to-many relationship)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_integrations (
                id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                integration_type TEXT NOT NULL,
                integration_config TEXT, -- JSON string for config
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
            )
        ''')
        
        # User integrations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_integrations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                integration_type TEXT NOT NULL, -- 'google_sheets', 'airtable', etc.
                integration_config TEXT, -- JSON string for config (encrypted sensitive data)
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync TIMESTAMP,
                sync_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # API keys table for user API access
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                key_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # User sessions table for secure session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Activity log for security and debugging
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT, -- JSON string
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions (session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log (created_at)')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")


class UserManager:
    """Manage user accounts and authentication"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_user(self, email: str, password: str, name: str) -> Optional[str]:
        """Create a new user account"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                conn.close()
                return None  # User already exists
            
            user_id = str(uuid.uuid4())
            password_hash = generate_password_hash(password)
            verification_token = secrets.token_urlsafe(32)
            
            print(f"Creating user: {email} with ID: {user_id}")  # Debug log
            
            cursor.execute('''
                INSERT INTO users (id, email, password_hash, name, verification_token)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, email, password_hash, name, verification_token))
            
            # Create default user profile
            profile_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO user_profiles (id, user_id)
                VALUES (?, ?)
            ''', (profile_id, user_id))
            
            # CRITICAL: Ensure transaction is committed
            conn.commit()
            print(f"User created successfully: {user_id}")  # Debug log
            
            # Verify user was actually inserted
            cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
            count = cursor.fetchone()[0]
            print(f"User count verification: {count}")  # Debug log
            
            conn.close()
            
            # Log activity
            self.log_activity(user_id, 'user_created', 'user', user_id)
            
            return user_id
        except Exception as e:
            print(f"Error creating user: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user info"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, password_hash, name, is_active, email_verified
                FROM users WHERE email = ?
            ''', (email,))
            
            user = cursor.fetchone()
            if not user or not user['is_active']:
                return None
            
            if check_password_hash(user['password_hash'], password):
                # Update last login
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user['id'],))
                conn.commit()
                
                user_dict = dict(user)
                conn.close()
                
                # Log activity
                self.log_activity(user['id'], 'user_login', 'user', user['id'])
                
                return user_dict
            
            conn.close()
            return None
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, name, is_active, created_at, last_login, email_verified
                FROM users WHERE id = ? AND is_active = 1
            ''', (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            return dict(user) if user else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, name, is_active, created_at, last_login, email_verified
                FROM users WHERE email = ? AND is_active = 1
            ''', (email,))
            
            user = cursor.fetchone()
            conn.close()
            
            return dict(user) if user else None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user information"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            allowed_fields = ['name', 'email']
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                self.log_activity(user_id, 'user_updated', 'user', user_id, {'fields': list(updates.keys())})
            
            return success
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Verify old password
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user or not check_password_hash(user['password_hash'], old_password):
                return False
            
            # Update password
            new_password_hash = generate_password_hash(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_password_hash, user_id))
            
            conn.commit()
            conn.close()
            
            self.log_activity(user_id, 'password_changed', 'user', user_id)
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
            return False
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                self.log_activity(user_id, 'user_deactivated', 'user', user_id)
            
            return success
        except Exception as e:
            print(f"Error deactivating user: {e}")
            return False
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False
    
    def log_activity(self, user_id: Optional[str], action: str, resource_type: Optional[str] = None, 
                    resource_id: Optional[str] = None, details: Optional[Dict] = None,
                    ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log user activity"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            activity_id = str(uuid.uuid4())
            details_json = json.dumps(details) if details else None
            
            cursor.execute('''
                INSERT INTO activity_log 
                (id, user_id, action, resource_type, resource_id, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (activity_id, user_id, action, resource_type, resource_id, 
                  details_json, ip_address, user_agent))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging activity: {e}")


class SessionManager:
    """Manage user sessions securely"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_session(self, user_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[str]:
        """Create a new session for user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            session_id = str(uuid.uuid4())
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)  # End of day
            
            cursor.execute('''
                INSERT INTO user_sessions 
                (id, user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, user_id, session_token, expires_at, ip_address, user_agent))
            
            conn.commit()
            conn.close()
            
            return session_token
        except Exception as e:
            print(f"Error creating session: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """Validate session and return user_id if valid"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, expires_at FROM user_sessions 
                WHERE session_token = ? AND is_active = 1
            ''', (session_token,))
            
            session = cursor.fetchone()
            if not session:
                return None
            
            # Check if expired
            expires_at = datetime.fromisoformat(session['expires_at'])
            if datetime.now() > expires_at:
                # Deactivate expired session
                cursor.execute('''
                    UPDATE user_sessions SET is_active = 0 
                    WHERE session_token = ?
                ''', (session_token,))
                conn.commit()
                conn.close()
                return None
            
            # Update last activity
            cursor.execute('''
                UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_token = ?
            ''', (session_token,))
            
            conn.commit()
            user_id = session['user_id']
            conn.close()
            
            return user_id
        except Exception as e:
            print(f"Error validating session: {e}")
            return None
    
    def delete_session(self, session_token: str) -> bool:
        """Delete/deactivate session"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions SET is_active = 0 
                WHERE session_token = ?
            ''', (session_token,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def delete_user_sessions(self, user_id: str) -> bool:
        """Delete all sessions for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions SET is_active = 0 
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting user sessions: {e}")
            return False
    
    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a specific session"""
        return self.delete_session(session_token)
    
    def is_valid_session(self, session_token: str, user_id: str) -> bool:
        """Check if session is valid for specific user"""
        validated_user_id = self.validate_session(session_token)
        return validated_user_id == user_id
    
    def update_session_activity(self, session_token: str) -> bool:
        """Update session last activity"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_token = ? AND is_active = 1
            ''', (session_token,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            print(f"Error updating session activity: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Cleanup expired sessions"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions SET is_active = 0 
                WHERE expires_at < CURRENT_TIMESTAMP AND is_active = 1
            ''')
            
            cleaned_count = cursor.rowcount
            conn.commit()
            conn.close()
            return cleaned_count
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            return 0
    
    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_sessions 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            
            sessions = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return sessions
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []

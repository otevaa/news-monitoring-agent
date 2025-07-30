"""
Enhanced Security Manager for NewsMonitor Pro
"""
import os
import secrets
import hashlib
import base64
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import request, session
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


class SecurityManager:
    """Enhanced security manager with encryption and secure storage"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.cipher_suite = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get master key from environment or create one in memory"""
        # Try to get from environment first
        key_env = os.environ.get('NEWSMONITOR_MASTER_KEY')
        if key_env:
            try:
                return base64.b64decode(key_env.encode())
            except:
                pass
        
        # Generate a key for this session only
        key = Fernet.generate_key()
        # Store in environment for this session
        os.environ['NEWSMONITOR_MASTER_KEY'] = base64.b64encode(key).decode()
        return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like API keys, credentials"""
        if not data:
            return ""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return ""
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return ""
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt or fallback to pbkdf2"""
        if HAS_BCRYPT:
            import bcrypt
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        else:
            # Fallback to PBKDF2
            salt = secrets.token_hex(16)
            pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return f"{salt}${pwd_hash.hex()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            if HAS_BCRYPT and not '$' in hashed:
                import bcrypt
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            else:
                # PBKDF2 verification
                salt, pwd_hash = hashed.split('$')
                computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
                return pwd_hash == computed_hash.hex()
        except Exception:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self) -> tuple[str, str]:
        """Generate API key and its hash"""
        api_key = f"nm_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, key_hash
    
    def validate_api_key(self, api_key: str, stored_hash: str) -> bool:
        """Validate API key against stored hash"""
        computed_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return secrets.compare_digest(computed_hash, stored_hash)
    
    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(64)
    
    def get_client_fingerprint(self) -> str:
        """Generate client fingerprint for additional security"""
        if not request:
            return "unknown"
        
        components = [
            request.headers.get('User-Agent', ''),
            request.headers.get('Accept-Language', ''),
            request.remote_addr or '',
        ]
        
        fingerprint_data = '|'.join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
    
    def is_secure_request(self) -> bool:
        """Check if request is secure (HTTPS in production)"""
        if os.getenv('FLASK_ENV') == 'development':
            return True
        return request.is_secure if request else False
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path components and dangerous characters
        filename = os.path.basename(filename)
        filename = "".join(c for c in filename if c.isalnum() or c in '._-')
        return filename[:100]  # Limit length
    
    def validate_input(self, data: str, max_length: int = 1000) -> bool:
        """Basic input validation"""
        if not data or len(data) > max_length:
            return False
        
        # Check for common injection patterns
        dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=', '../', '..\\']
        data_lower = data.lower()
        
        for pattern in dangerous_patterns:
            if pattern in data_lower:
                return False
        
        return True
    
    def log_security_event(self, event_type: str, details: Dict, user_id: Optional[str] = None):
        """Log security events for monitoring"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': event_type,
            'user_id': user_id,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'details': details
        }
        
        # In production, send to proper logging system
        print(f"[SECURITY] {json.dumps(event)}")


class SecureCredentialManager:
    """Manage credentials securely without file storage"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security = security_manager
        self.credentials_cache = {}
    
    def store_credential(self, user_id: str, service: str, credential_data: Dict) -> bool:
        """Store encrypted credential in database"""
        try:
            encrypted_data = self.security.encrypt_sensitive_data(json.dumps(credential_data))
            
            # Store in database instead of file
            # This will be implemented with the database manager
            cache_key = f"{user_id}:{service}"
            self.credentials_cache[cache_key] = encrypted_data
            
            self.security.log_security_event(
                'credential_stored', 
                {'service': service}, 
                user_id
            )
            return True
            
        except Exception as e:
            self.security.log_security_event(
                'credential_store_failed', 
                {'service': service, 'error': str(e)}, 
                user_id
            )
            return False
    
    def get_credential(self, user_id: str, service: str) -> Optional[Dict]:
        """Retrieve and decrypt credential"""
        try:
            cache_key = f"{user_id}:{service}"
            encrypted_data = self.credentials_cache.get(cache_key)
            
            if not encrypted_data:
                return None
            
            decrypted_data = self.security.decrypt_sensitive_data(encrypted_data)
            return json.loads(decrypted_data) if decrypted_data else None
            
        except Exception as e:
            self.security.log_security_event(
                'credential_retrieval_failed', 
                {'service': service, 'error': str(e)}, 
                user_id
            )
            return None
    
    def remove_credential(self, user_id: str, service: str) -> bool:
        """Remove credential securely"""
        try:
            cache_key = f"{user_id}:{service}"
            if cache_key in self.credentials_cache:
                del self.credentials_cache[cache_key]
            
            self.security.log_security_event(
                'credential_removed', 
                {'service': service}, 
                user_id
            )
            return True
            
        except Exception as e:
            self.security.log_security_event(
                'credential_removal_failed', 
                {'service': service, 'error': str(e)}, 
                user_id
            )
            return False


class RateLimiter:
    """Rate limiting for API and login attempts"""
    
    def __init__(self):
        self.attempts = {}
        self.blocked_ips = {}
    
    def is_rate_limited(self, key: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if key is rate limited"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old attempts
        if key in self.attempts:
            self.attempts[key] = [
                attempt_time for attempt_time in self.attempts[key] 
                if attempt_time > window_start
            ]
        
        # Check current attempts
        current_attempts = len(self.attempts.get(key, []))
        return current_attempts >= max_attempts
    
    def record_attempt(self, key: str):
        """Record an attempt"""
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(datetime.utcnow())
    
    def block_ip(self, ip: str, duration_minutes: int = 60):
        """Block IP for specified duration"""
        self.blocked_ips[ip] = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if ip in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False

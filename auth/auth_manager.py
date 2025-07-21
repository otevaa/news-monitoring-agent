"""
Enhanced Authentication and Security System for NewsMonitor Pro
"""
from flask import session, request, redirect, url_for, flash
from functools import wraps
from typing import Optional, Dict, Tuple
import secrets
import os
import json
import uuid
from datetime import datetime, timedelta
from database.models import DatabaseManager, UserManager, SessionManager
from database.managers import DatabaseUserProfileManager, DatabaseIntegrationManager
from auth.security_manager import SecurityManager, SecureCredentialManager, RateLimiter


class EnhancedAuthManager:
    """Enhanced authentication manager with strong security"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.user_manager = UserManager(self.db_manager)
        self.session_manager = SessionManager(self.db_manager)
        self.profile_manager = DatabaseUserProfileManager(self.db_manager)
        self.integration_manager = DatabaseIntegrationManager(self.db_manager)
        self.security = SecurityManager()
        self.credential_manager = SecureCredentialManager(self.security)
        self.rate_limiter = RateLimiter()
    
    def register_user(self, email: str, password: str, name: str) -> Optional[str]:
        """Register a new user with enhanced security"""
        # Validate input
        if not self.security.validate_input(email, 254) or not self.security.validate_input(name, 100):
            return None
        
        # Check rate limiting
        client_ip = request.remote_addr if request else 'unknown'
        if self.rate_limiter.is_rate_limited(f"register_{client_ip}", max_attempts=3, window_minutes=60):
            return None
        
        self.rate_limiter.record_attempt(f"register_{client_ip}")
        
        user_id = self.user_manager.create_user(email, password, name)
        if user_id:
            # Create default profile
            self.profile_manager.create_default_profile(user_id)
            
            # Log security event
            self.security.log_security_event(
                'user_registered',
                {'email': email, 'name': name},
                user_id
            )
        
        return user_id
    
    def login_user(self, username: str, password: str, request_obj) -> Tuple[bool, str]:
        """Enhanced login with security checks"""
        # Get client IP
        client_ip = request_obj.environ.get('HTTP_X_FORWARDED_FOR', 
                                          request_obj.environ.get('REMOTE_ADDR', 'unknown'))
        
        # Ensure client_ip is not None
        if client_ip is None:
            client_ip = 'unknown'
        
        # Check rate limiting
        if self.rate_limiter.is_ip_blocked(client_ip):
            return False, "Trop de tentatives de connexion. Essayez plus tard."
        
        # Validate user credentials using authenticate_user method
        user = self.user_manager.authenticate_user(username, password)
        if not user:
            self.rate_limiter.block_ip(client_ip, duration_minutes=30)
            return False, "Nom d'utilisateur ou mot de passe incorrect"
        
        # Create session
        session_token = self.session_manager.create_session(
            user['id'], 
            client_ip, 
            request_obj.headers.get('User-Agent', 'Unknown')
        )
        
        if not session_token:
            return False, "Erreur lors de la création de la session"
        
        # Store in Flask session
        session['user_id'] = user['id']
        session['session_token'] = session_token
        session['username'] = user['email']
        session['client_fingerprint'] = self.security.get_client_fingerprint()
        session['client_fingerprint'] = self.security.get_client_fingerprint()
        
        # Update last login
        self.user_manager.update_last_login(user['id'])
        
        # Clean up old files for security
        self._cleanup_temp_credentials()
        
        return True, "Connexion réussie"
    
    def logout_user(self, user_id: Optional[str] = None) -> bool:
        """Logout user and clean up session"""
        user_id = user_id or session.get('user_id')
        if not user_id:
            return False
        
        if 'session_token' in session:
            self.session_manager.delete_session(session['session_token'])
        
        # Clear all session data
        session.clear()
        
        # Clear any Google OAuth credentials files (security improvement)
        self._cleanup_temp_credentials()
        
        return True
    
    def require_auth(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                return redirect(url_for('signin'))
            return f(*args, **kwargs)
        return decorated_function
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with enhanced security"""
        user_id = session.get('user_id')
        session_token = session.get('session_token')
        stored_fingerprint = session.get('client_fingerprint')
        
        if not all([user_id, session_token]):
            return False
        
        # Verify client fingerprint
        current_fingerprint = self.security.get_client_fingerprint()
        if stored_fingerprint != current_fingerprint:
            self.security.log_security_event(
                'session_fingerprint_mismatch',
                {'stored': stored_fingerprint, 'current': current_fingerprint},
                user_id
            )
            self.logout_user()
            return False
        
        # Verify session in database - ensure we have valid strings
        if not isinstance(session_token, str) or not isinstance(user_id, str):
            self.logout_user()
            return False
            
        if not self.session_manager.is_valid_session(session_token, user_id):
            self.logout_user()
            return False
        
        # Update session activity
        self.session_manager.update_session_activity(session_token)
        
        return True
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user"""
        if not self.is_authenticated():
            return None
        
        user_id = session.get('user_id')
        if not user_id:
            return None
            
        return self.user_manager.get_user_by_id(user_id)
    
    def store_integration_credential(self, user_id: str, service: str, credentials: Dict) -> bool:
        """Store integration credentials securely"""
        return self.credential_manager.store_credential(user_id, service, credentials)
    
    def get_integration_credential(self, user_id: str, service: str) -> Optional[Dict]:
        """Get integration credentials securely"""
        return self.credential_manager.get_credential(user_id, service)
    
    def cleanup_expired_sessions(self):
        """Cleanup expired sessions (run periodically)"""
        self.session_manager.cleanup_expired_sessions()
        
    def get_security_stats(self, user_id: str) -> Dict:
        """Get security statistics for user"""
        sessions = self.session_manager.get_user_sessions(user_id)
        
        return {
            'active_sessions': len([s for s in sessions if s['is_active']]),
            'total_sessions': len(sessions),
            'last_login': sessions[0]['created_at'] if sessions else None,
            'login_locations': list(set([s['ip_address'] for s in sessions if s['ip_address']]))
        }

    def _cleanup_temp_credentials(self):
        """Clean up temporary credential files for security"""
        temp_files = [
            'user_credentials.json',
            '.secure_credentials',
            'campaigns.json',
            'user_profiles.json'
        ]
        
        for file in temp_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    print(f"Cleaned up temporary file: {file}")
                except Exception as e:
                    print(f"Error cleaning up {file}: {e}")


# Global auth manager instance
auth_manager = EnhancedAuthManager()

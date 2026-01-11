from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

"""
Extensions module
This module initializes Flask extensions that are used across the application to avoid circular imports.
"""

# Mail instance (not actively used, SendGrid API is used instead)
mail = Mail()

# CSRF Protection
csrf = CSRFProtect()

# Rate Limiter - ป้องกัน brute force และ spam
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
from flask_mail import Mail

"""
Extensions module
This module initializes Flask extensions that are used across the application to avoid circular imports.
"""

# สร้างตัวแปร mail รอไว้เฉยๆ ยังไม่ต้องทำอะไร
mail = Mail()
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "ZnW7WvTZj/LBN/p9PCSrEWNEdqok62Zr7W39BH2Z03pFo/FAdOIYBYlYSYJOizeH"
ALGORITHM = "HS256"

payload = {
    "sub": "testuser",         # Use a username or user id your backend expects
    "roles": ["ROLE_USER"],    # Or whatever roles your app expects
    "exp": datetime.utcnow() + timedelta(hours=8)  # Token valid for 8 hours
}

token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

print(token)
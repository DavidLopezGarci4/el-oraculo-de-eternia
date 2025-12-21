import bcrypt

def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt."""
    if not plain_password:
        return ""
    # bcrypt requires bytes
    pwd_bytes = plain_password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed string."""
    if not plain_password or not hashed_password:
        return False
    
    # Check if legacy plain text (migration layer)
    # If it doesn't look like a bcrypt hash (usually starts with $2b$), we assume it might be legacy plain
    # BUT for security, we should ideally force update. 
    # For this transition, if verification fails as hash, we try plain comparison? NO, dangerous.
    # We will assume new users are hashed. Existing "eternia" hardcoded check handles bootstrapping.
    
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

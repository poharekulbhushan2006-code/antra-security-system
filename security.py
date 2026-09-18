import hashlib
import secrets
import math
from typing import List, Dict, Any, Tuple, Optional
from config import FACE_MATCH_THRESHOLD

def generate_salt(length: int = 16) -> str:
    return secrets.token_hex(length)

def hash_pin(pin: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Cryptographically hashes a PIN / password using PBKDF2 HMAC SHA-256 with 100,000 iterations.
    Returns (pin_hash, salt).
    """
    if not salt:
        salt = generate_salt()
    
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        pin.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    )
    return derived.hex(), salt

def verify_pin(provided_pin: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verifies a PIN against the stored hash and salt using constant-time digest comparison.
    """
    calculated_hash, _ = hash_pin(provided_pin, stored_salt)
    return secrets.compare_digest(calculated_hash, stored_hash)

def euclidean_distance(v1: List[float], v2: List[float]) -> float:
    """
    Computes Euclidean distance between two 128-dimensional face embedding vectors.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 999.0
    
    total = sum((a - b) ** 2 for a, b in zip(v1, v2))
    return math.sqrt(total)

def match_face_descriptor(
    query_descriptor: List[float],
    registered_users: List[Dict[str, Any]],
    threshold: float = FACE_MATCH_THRESHOLD
) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """
    Compares the query face descriptor against all registered users.
    Returns (is_match, matched_user_dict, best_distance).
    """
    if not query_descriptor or not registered_users:
        return False, None, 999.0

    best_match = None
    min_dist = 999.0

    for user in registered_users:
        user_desc = user.get("face_descriptor")
        if not user_desc or len(user_desc) != len(query_descriptor):
            continue
            
        dist = euclidean_distance(query_descriptor, user_desc)
        if dist < min_dist:
            min_dist = dist
            best_match = user

    # A lower distance means closer resemblance
    is_match = (min_dist <= threshold) and (best_match is not None)
    return is_match, (best_match if is_match else None), min_dist

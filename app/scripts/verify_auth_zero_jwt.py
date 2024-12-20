import jwt
import requests
from jwt import InvalidTokenError, ExpiredSignatureError
from app.config import settings

ALGORITHMS = [
    "RS256"
]

def get_jwks():
    """
    Fetch JWKS keys from Auth0's endpoint.
    """
    jwks_url = f"https://{settings.auth_zero_issuer_domain}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    response.raise_for_status()
    return response.json()


def verify_jwt(token):
    """
    Verify the JWT token.
    """
    try:
        # Fetch the JWKS
        jwks = get_jwks()

        # Get the kid (Key ID) from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise InvalidTokenError("Missing 'kid' in token header.")

        # Find the public key in JWKS that matches the 'kid'
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            raise InvalidTokenError("Unable to find matching public key for 'kid'.")

        # Decode and verify the token
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=ALGORITHMS,
            audience=settings.auth_zero_audience,
            issuer=f"https://{settings.auth_zero_issuer_domain}/"
        )

        return decoded_token

    except ExpiredSignatureError:
        return {"error": "Token has expired."}
    except InvalidTokenError as e:
        return {"error": str(e)}

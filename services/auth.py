import logging
from datetime import datetime, timedelta, timezone
import jwt
from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_access_token_expire_minutes

    def create_access_token(self, account_id: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.expire_minutes
        )

        payload = {"sub": str(account_id), "exp": expire}

        encoded_jwt = jwt.encode(
            payload, self.secret_key, algorithm=self.algorithm
        )
        return encoded_jwt

    def verify_access_token(self, token: str) -> int | None:
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            account_id_str = payload.get("sub")
            if account_id_str is None:
                return None

            return int(account_id_str)

        except jwt.ExpiredSignatureError:
            logger.warning("попытка использования истекшего jwt")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"попытка использования невалидного jwt: {e}")
            return None
        except Exception as e:
            logger.error(f"непредвиденная ошибка при проверке токена: {e}")
            return None

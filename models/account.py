from pydantic import BaseModel, Field


class AccountCreateRequestDto(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)


class AccountResponseDto(BaseModel):
    id: int
    login: str
    is_blocked: bool


class LoginRequestDto(BaseModel):
    login: str = Field(..., description="Логин пользователя")
    password: str = Field(..., description="Пароль пользователя")

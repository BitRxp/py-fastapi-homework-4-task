from datetime import date
from typing import Annotated
from enum import Enum

from fastapi import UploadFile, Form, File
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator, ConfigDict, HttpUrl, ValidationError

from database.models.accounts import GenderEnum
from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date,
)


class ProfileCreateSchema(BaseModel):
    first_name: str
    last_name: str
    gender: GenderEnum
    date_of_birth: date
    info: str
    avatar: UploadFile

    model_config = ConfigDict(from_attributes=True)

    @field_validator("first_name", "last_name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        validate_name(value)
        return value.strip().lower()

    @field_validator("gender", mode="before")
    @classmethod
    def _validate_gender(cls, value: GenderEnum | str) -> GenderEnum:
        raw = value.value if isinstance(value, Enum) else str(value)
        validate_gender(raw)
        return GenderEnum(raw)

    @field_validator("date_of_birth")
    @classmethod
    def _validate_date_of_birth(cls, date_of_birth: date) -> date:
        validate_birth_date(date_of_birth)
        return date_of_birth

    @field_validator("avatar")
    @classmethod
    def _validate_avatar(cls, value: UploadFile) -> UploadFile:
        validate_image(value)
        return value

    @field_validator("info")
    @classmethod
    def _validate_info(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Info field cannot be empty or contain only spaces.")
        return value

    @classmethod
    def as_form(
        cls,
        first_name: Annotated[str, Form(...)],
        last_name: Annotated[str, Form(...)],
        gender: Annotated[str, Form(...)],
        date_of_birth: Annotated[date, Form(...)],
        info: Annotated[str, Form(...)],
        avatar: Annotated[UploadFile, File(...)],
    ) -> "ProfileCreateSchema":
        try:
            return cls(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=date_of_birth,
                info=info,
                avatar=avatar,
            )
        except ValidationError as e:
            simplified = []
            for err in e.errors():
                simplified.append(
                    {
                        "loc": err.get("loc"),
                        "msg": err.get("msg"),
                        "type": err.get("type"),
                    }
                )
            raise RequestValidationError(simplified) from e
        except Exception:
            raise RequestValidationError(
                [{"loc": ("body",), "msg": "Invalid form data", "type": "value_error"}]
            )


class ProfileResponseSchema(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    gender: GenderEnum
    date_of_birth: date
    info: str
    avatar: HttpUrl | str

    model_config = ConfigDict(from_attributes=True)

import re
from datetime import date

from database.models.accounts import GenderEnum
from typing import Annotated
from enum import Enum
from fastapi import UploadFile, Form, File
from pydantic import BaseModel, field_validator, ConfigDict, HttpUrl

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

    model_config = {"from_attributes": True}

    @field_validator("first_name", "last_name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        validate_name(value)
        return value.strip().lower()

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: GenderEnum | str) -> GenderEnum | str:
        validate_gender(value.value if isinstance(value, Enum) else value)
        return value

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
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar,
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

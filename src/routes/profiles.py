from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from config import get_s3_storage_client, get_jwt_auth_manager

from schemas import ProfileCreateSchema, ProfileResponseSchema

from database import (
    get_db,
    UserModel,
    UserProfileModel,
)

from storages import S3StorageInterface

from exceptions import TokenExpiredError, InvalidTokenError

from security.interfaces import JWTAuthManagerInterface

router = APIRouter(prefix="/users")


async def get_current_user(
    request: Request,
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
        )
    token = auth_header.split("Bearer ")[1]

    try:
        payload = jwt_manager.decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == user_id)
        .options(joinedload(UserModel.group))
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active",
        )
    return user


@router.post(
    "/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new profile",
)
async def create_profile(
    user_id: int,
    profile: ProfileCreateSchema = Depends(ProfileCreateSchema.as_form),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
) -> ProfileResponseSchema:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    existing = await db.execute(
        select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Profile already exists"
        )

    avatar_bytes = await profile.avatar.read()
    file_name = f"avatars/{user_id}_avatar.jpg"
    await s3_client.upload_file(file_name, avatar_bytes)
    avatar_url = await s3_client.get_file_url(file_name)

    new_profile = UserProfileModel(
        user_id=user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info.strip(),
        avatar=avatar_url,
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return ProfileResponseSchema.model_validate(new_profile)

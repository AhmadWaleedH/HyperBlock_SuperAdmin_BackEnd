from fastapi import APIRouter
from .users import router as users_router
from .auth import router as auth_router
from .guilds import router as guilds_router
from .contests import router as contests_router
from .raffles import router as raffles_router
from .auctions import router as auctions_router
from .shop import router as shop_router
from .embed_messages import router as embed_messages_router
from .subscriptions import router as subscriptions_router
from .guild_subscriptions import router as guild_subscriptions_router
from .scheduler import router as scheduler_router

router = APIRouter()

router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(guilds_router, prefix="/guilds", tags=["guilds"])
router.include_router(contests_router, prefix="/contests", tags=["contests"])
router.include_router(raffles_router, prefix="/raffles", tags=["raffles"])
router.include_router(auctions_router, prefix="/auctions", tags=["auctions"])
router.include_router(shop_router, prefix="/shop", tags=["shop"])
router.include_router(embed_messages_router, prefix="/embeds", tags=["embeds"])
router.include_router(subscriptions_router, prefix="/subscriptions", tags=["Subscriptions"])
router.include_router(guild_subscriptions_router, prefix="/guild-subscriptions", tags=["Guild Subscriptions"])
router.include_router(scheduler_router, prefix="/scheduler", tags=["scheduler"])
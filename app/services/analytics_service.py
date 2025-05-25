"""
Analytics service for calculating guild metrics
Following the detailed calculation formulas for community scoring
"""
import logging
import math
from datetime import datetime, timedelta
from app.db.database import get_database
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# Define constants for calculations
# These weights should be configured according to your business requirements
WEIGHTS = {
    # CAS weights
    "active_members_weight": 0.3,
    "social_engagement_weight": 0.2,
    "event_participation_weight": 0.2,
    "announcement_frequency_weight": 0.05,
    "event_frequency_weight": 0.1,
    "social_task_frequency_weight": 0.05,
    "ease_of_earning_points_weight": 0.1,
    "store_update_frequency_weight": 0.05,
    "auction_update_frequency_weight": 0.05,
    
    # CHS weights
    "community_size_weight": 0.6,
    "community_age_weight": 0.4,
    
    # EAS weights
    "community_points_from_sale_weight": 0.3,
    "hpbp_from_sale_weight": 0.3,
    "hpbp_from_exchange_weight": 0.3,
    "community_points_from_vault_weight": 0.1,
    
    # CCS weights (combined score)
    "community_activity_weight": 0.5,
    "community_health_weight": 0.3,
    "exchange_activity_weight": 0.2,
    
    # ERC parameters (exchange rate calculation)
    "min_rate": 0.01,
    "max_rate": 0.1,
    "steepness": 5.0,
    "center": 50.0,
}

async def calculate_guild_analytics():
    """
    Calculate analytics metrics for all guilds
    Updates these values in GuildAnalytics:
    - CAS (Community Activity Score)
    - CHS (Community Health Score)
    - EAS (Exchange Activity Score)
    - CCS (Community Contribution Score - Combined Community Score)
    - ERC (Exchange Rate Calculation)
    - vault (Guild Vault Points)
    - reservedPoints (Reserved Points)
    """
    logger.info("Starting guild analytics calculation job")
    db = await get_database()
    
    # Get all guilds - use correct Motor pattern
    guilds_cursor = db.guilds.find({})
    guilds = await guilds_cursor.to_list(length=None)
    
    if not guilds:
        logger.warning("No guilds found in database")
        return 0
        
    logger.info(f"Found {len(guilds)} guilds in database")
    
    # Get maximum values across all guilds for normalization
    max_community_size = 1  # Default to 1 to avoid division by zero
    max_community_age = 1   # Default to 1 to avoid division by zero
    
    # First pass to find maximums
    for guild in guilds:
        community_size = guild.get("totalMembers")
        if community_size is None:
            community_size = 0
        if community_size > max_community_size:
            max_community_size = community_size
            
        created_date = guild.get("createdAt", datetime.now())
        community_age = (datetime.now() - created_date).days
        if community_age > max_community_age:
            max_community_age = community_age
    
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    seven_days_ago = now - timedelta(days=7)
    
    updated_count = 0
    
    for guild in guilds:
        guild_id = guild.get("_id")
        guild_discord_id = guild.get("guildId")
        guild_name = guild.get("guildName", "Unknown Guild")
        
        try:
            logger.info(f"Processing analytics for guild: {guild_name} (ID: {guild_discord_id})")
            
            # Get user activity data for this guild
            users_cursor = db.users.find({
                "serverMemberships.guildId": guild_discord_id
            })
            server_members = await users_cursor.to_list(length=None)
            
            logger.info(f"Found {len(server_members)} members for guild: {guild_name}")
            
            # Calculate required metrics for formulas
            total_members = guild.get("totalMembers", 0) or 1  # Default to 1 if 0 to avoid division by zero
            
            # Calculate active members (members who have been active in the last 30 days)
            active_members = 0
            social_engagers = 0
            
            for user in server_members:
                # Get the specific server membership for this guild
                guild_membership = next((sm for sm in user.get("serverMemberships", []) 
                                        if sm.get("guildId") == guild_discord_id), None)
                
                if guild_membership:
                    # Check if user is active
                    is_active = guild_membership.get("counter", {}).get("activeParticipant", False)
                    if is_active:
                        active_members += 1
                        
                        # Check if user has engaged with social tasks
                        if (guild_membership.get("completedTasks") or 0) > 0:
                            social_engagers += 1
            
            # Make sure we have at least 1 active member to avoid division by zero
            active_members = max(active_members, 1)
            logger.info(f"Active members: {active_members}, Social engagers: {social_engagers}")
            
            # Get recent events data
            # Check if events collection exists first
            events_cursor = db.events.find({
                "guildId": guild_discord_id,
                "createdAt": {"$gte": thirty_days_ago}
            })
            
            # Use an empty list if there are no events or the collection doesn't exist
            try:
                recent_events = await events_cursor.to_list(length=None)
                event_participants = sum(event.get("participantCount", 0) for event in recent_events)
                event_frequency = len(recent_events) / 30.0  # Events per day
                logger.info(f"Found {len(recent_events)} events in the last 30 days")
            except Exception as e:
                logger.warning(f"Error getting events, using default values: {e}")
                recent_events = []
                event_participants = 0
                event_frequency = 0
            
            # Check if community should be delisted (no events in last 60 days)
            try:
                events_sixty_cursor = db.events.find({
                    "guildId": guild_discord_id,
                    "createdAt": {"$gte": sixty_days_ago}
                })
                recent_events_sixty_days = await events_sixty_cursor.to_list(length=None)
                should_delist = len(recent_events_sixty_days) == 0
            except Exception as e:
                logger.warning(f"Error checking events for delisting, using default: {e}")
                should_delist = False
            
            # Get announcement frequency (from counter in guild object)
            counter = guild.get("counter", {})
            announcement_count = counter.get("announcementCount", 0)
            weekly_announcement_freq = counter.get("weeklyAnnouncementFrequency", 0)
            announcement_frequency = weekly_announcement_freq / 7.0  # Convert to daily frequency
            
            # Get social task frequency
            social_task_count = counter.get("socialTasksCount", 0)
            weekly_social_task_freq = counter.get("weeklySocialTasksCounter", 0)
            social_task_frequency = weekly_social_task_freq / 7.0  # Convert to daily
            
            # Get store and auction update frequency
            store_update_count = counter.get("storeUpdateCount", 0)
            weekly_store_update_freq = counter.get("weeklyStoreUpdateFrequency", 0)
            store_update_frequency = weekly_store_update_freq / 7.0  # Convert to daily
            
            auction_update_count = counter.get("auctionUpdateCount", 0)
            weekly_auction_update_freq = counter.get("weeklyAuctionUpdateFrequency", 0)
            auction_update_frequency = weekly_auction_update_freq / 7.0  # Convert to daily
            
            logger.info(f"Announcement freq: {announcement_frequency}, Event freq: {event_frequency}, Store update freq: {store_update_frequency}")
            
            # Calculate ease of earning points
            # Try to get point transactions, use defaults if collection doesn't exist
            try:
                point_txs_cursor = db.point_transactions.find({
                    "guildId": guild_discord_id,
                    "timestamp": {"$gte": thirty_days_ago}
                })
                point_transactions = await point_txs_cursor.to_list(length=None)
                total_points_given = sum(tx.get("amount", 0) for tx in point_transactions 
                                       if tx.get("type") == "reward")
            except Exception as e:
                logger.warning(f"Error getting point transactions, using default values: {e}")
                point_transactions = []
                total_points_given = 0
            
            # Ease of earning points is the average points given per active member per day
            # If no points given, consider it difficult to earn points (low value is better)
            if total_points_given > 0:
                ease_of_earning_points = (total_points_given / active_members / 30.0) / 100.0
                # Scale to 0-1 range, with 1 being very easy to earn points
                ease_of_earning_points = min(1.0, ease_of_earning_points)
            else:
                ease_of_earning_points = 0.1  # Default low value
            
            # Get guild age in days
            created_date = guild.get("createdAt", datetime.now())
            community_age = (now - created_date).days
            community_age = max(community_age, 1)  # Ensure at least 1 day old
            
            # Get vault and reserved points
            try:
                vault_points = await calculate_guild_vault(guild_discord_id)
                reserved_points = await calculate_reserved_points(guild_discord_id)
            except Exception as e:
                logger.warning(f"Error calculating vault/reserved points, using defaults: {e}")
                vault_points = 1000  # Default value
                reserved_points = 200  # Default value
            
            # Use simple defaults for exchange-related metrics
            community_points_from_sales = 100
            hpbp_from_sales = 50
            hpbp_from_exchange = 25
            community_points_from_vault = 10
            
            # Try to get these values if collections exist
            try:
                community_points_from_sales = await calculate_points_from_sales(guild_discord_id)
                hpbp_from_sales = await calculate_hpbp_from_sales(guild_discord_id)
                hpbp_from_exchange = await calculate_hpbp_from_exchange(guild_discord_id)
                community_points_from_vault = await calculate_points_from_vault(guild_discord_id)
            except Exception as e:
                logger.warning(f"Error calculating exchange metrics, using defaults: {e}")
            
            # Calculate Community Activity Score (CAS)
            cas = (
                WEIGHTS["active_members_weight"] * (active_members / total_members) +
                WEIGHTS["social_engagement_weight"] * (social_engagers / active_members) +
                WEIGHTS["event_participation_weight"] * (event_participants / active_members) +
                WEIGHTS["announcement_frequency_weight"] * announcement_frequency +
                WEIGHTS["event_frequency_weight"] * event_frequency +
                WEIGHTS["social_task_frequency_weight"] * social_task_frequency -
                WEIGHTS["ease_of_earning_points_weight"] * ease_of_earning_points +
                WEIGHTS["store_update_frequency_weight"] * store_update_frequency +
                WEIGHTS["auction_update_frequency_weight"] * auction_update_frequency
            )
            
            # Scale CAS to 0-100 range
            cas = max(0, min(100, cas * 100))
            
            # Calculate Community Health Score (CHS)
            chs = (
                WEIGHTS["community_size_weight"] * (total_members / max_community_size) +
                WEIGHTS["community_age_weight"] * (community_age / max_community_age)
            )
            
            # Scale CHS to 0-100 range
            chs = max(0, min(100, chs * 100))
            
            # Calculate Exchange Activity Score (EAS)
            # Avoid division by zero
            reserved_points_safe = max(1, reserved_points)
            
            eas = (
                WEIGHTS["community_points_from_sale_weight"] * (community_points_from_sales / reserved_points_safe) +
                WEIGHTS["hpbp_from_sale_weight"] * (hpbp_from_sales / reserved_points_safe) +
                WEIGHTS["hpbp_from_exchange_weight"] * (hpbp_from_exchange / reserved_points_safe) -
                WEIGHTS["community_points_from_vault_weight"] * (community_points_from_vault / reserved_points_safe)
            )
            
            # Scale EAS to 0-100 range and ensure it's not negative
            eas = max(0, min(100, eas * 100))
            
            # Calculate Combined Community Score (CCS)
            ccs = (
                WEIGHTS["community_activity_weight"] * cas +
                WEIGHTS["community_health_weight"] * chs +
                WEIGHTS["exchange_activity_weight"] * eas
            )
            
            # Calculate Exchange Rate Calculation (ERC)
            # Using sigmoid function: ERC = Min Rate + (Max Rate - Min Rate) * (1 / (1 + e^(-Steepness * (CCS - Center))))
            sigmoid_value = 1.0 / (1.0 + math.exp(-WEIGHTS["steepness"] * ((ccs - WEIGHTS["center"]) / 100.0)))
            erc = WEIGHTS["min_rate"] + (WEIGHTS["max_rate"] - WEIGHTS["min_rate"]) * sigmoid_value
            
            # Apply adjustments to ERC
            # 1. Recent Event Activity: At least 5 events in last 30 days
            if len(recent_events) < 5:
                erc = erc * 0.9  # Reduce by 10% if not enough events
            
            # 2. Delisting Condition: No events in last 60 days
            if should_delist:
                erc = 0  # Community is delisted from exchange
                logger.warning(f"Guild {guild_name} is being delisted due to inactivity (no events in 60 days)")
            
            # 3. Supply Adjustment for points from vault
            if community_points_from_vault > 0:
                # Severely decrease ERC if points are added from vault
                erc = erc * (1.0 - min(0.5, community_points_from_vault / reserved_points_safe))
            
            # Scale all metrics to integers (0-100)
            cas = int(round(cas))
            chs = int(round(chs))
            eas = int(round(eas))
            ccs = int(round(ccs))
            erc = int(round(erc * 100))  # Convert to percentage for storage
            
            logger.info(f"Final scores - CAS: {cas}, CHS: {chs}, EAS: {eas}, CCS: {ccs}, ERC: {erc}")
            
            # Update the guild with new analytics values
            update_result = await db.guilds.update_one(
                {"_id": guild_id},
                {"$set": {
                    "analytics.CAS": cas,
                    "analytics.CHS": chs,
                    "analytics.EAS": eas,
                    "analytics.CCS": ccs,
                    "analytics.ERC": erc,
                    "analytics.vault": vault_points,
                    "analytics.reservedPoints": reserved_points,
                    "updatedAt": datetime.now()
                }}
            )
            
            # Check if update was successful
            if update_result.modified_count > 0:
                logger.info(f"Successfully updated analytics for guild {guild_name}")
                updated_count += 1
            else:
                logger.warning(f"Guild {guild_name} was not updated (no changes or guild not found)")
            
        except Exception as e:
            logger.error(f"Error calculating analytics for guild {guild_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info(f"Completed guild analytics calculation. Updated {updated_count} guilds.")
    return updated_count

async def calculate_guild_vault(guild_id):
    """Calculate total points in guild's system"""
    db = await get_database()
    
    # Sum all points associated with this guild
    pipeline = [
        {"$match": {"serverMemberships.guildId": guild_id}},
        {"$unwind": "$serverMemberships"},
        {"$match": {"serverMemberships.guildId": guild_id}},
        {"$group": {"_id": None, "totalPoints": {"$sum": "$serverMemberships.points"}}}
    ]
    
    try:
        # Use aggregate with Motor pattern
        cursor = db.users.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        # Return the first result or default if no results
        if result and len(result) > 0:
            return result[0]["totalPoints"]
        else:
            return 0
    except Exception as e:
        logger.warning(f"Error calculating guild vault, returning default value: {e}")
        return 500  # Default value

async def calculate_reserved_points(guild_id):
    """Calculate reserved (allocated but not spent) points"""
    db = await get_database()
    
    # Try to calculate points reserved for raffles
    raffle_points = 0
    try:
        raffle_pipeline = [
            {"$match": {"guildId": guild_id, "status": {"$in": ["active", "pending"]}}},
            {"$group": {"_id": None, "totalReserved": {"$sum": "$pointsPool"}}}
        ]
        
        raffle_cursor = db.raffles.aggregate(raffle_pipeline)
        raffle_result = await raffle_cursor.to_list(length=None)
        
        if raffle_result and len(raffle_result) > 0:
            raffle_points = raffle_result[0]["totalReserved"]
    except Exception as e:
        logger.warning(f"Error calculating raffle points, using default: {e}")
    
    # Try to calculate points reserved for auctions
    auction_points = 0
    try:
        auction_pipeline = [
            {"$match": {"guildId": guild_id, "status": {"$in": ["active", "pending"]}}},
            {"$group": {"_id": None, "totalReserved": {"$sum": "$currentBid"}}}
        ]
        
        auction_cursor = db.auctions.aggregate(auction_pipeline)
        auction_result = await auction_cursor.to_list(length=None)
        
        if auction_result and len(auction_result) > 0:
            auction_points = auction_result[0]["totalReserved"]
    except Exception as e:
        logger.warning(f"Error calculating auction points, using default: {e}")
    
    return raffle_points + auction_points

async def calculate_points_from_sales(guild_id):
    """Calculate community points earned from sales"""
    db = await get_database()
    
    try:
        # This would need to be adjusted based on your specific data model
        pipeline = [
            {"$match": {"guildId": guild_id, "type": "sale", "status": "completed"}},
            {"$group": {"_id": None, "totalPoints": {"$sum": "$pointsEarned"}}}
        ]
        
        cursor = db.transactions.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        if result and len(result) > 0:
            return result[0]["totalPoints"]
        else:
            return 0
    except Exception as e:
        logger.warning(f"Error calculating points from sales, using default: {e}")
        return 100  # Default value

async def calculate_hpbp_from_sales(guild_id):
    """Calculate HyperBlock Points earned from sales"""
    db = await get_database()
    
    try:
        pipeline = [
            {"$match": {"guildId": guild_id, "type": "sale", "status": "completed"}},
            {"$group": {"_id": None, "totalHPBP": {"$sum": "$hpbpEarned"}}}
        ]
        
        cursor = db.transactions.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        if result and len(result) > 0:
            return result[0]["totalHPBP"]
        else:
            return 0
    except Exception as e:
        logger.warning(f"Error calculating HPBP from sales, using default: {e}")
        return 50  # Default value

async def calculate_hpbp_from_exchange(guild_id):
    """Calculate HyperBlock Points earned from exchanges"""
    db = await get_database()
    
    try:
        pipeline = [
            {"$match": {"guildId": guild_id, "type": "exchange", "status": "completed"}},
            {"$group": {"_id": None, "totalHPBP": {"$sum": "$hpbpEarned"}}}
        ]
        
        cursor = db.transactions.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        if result and len(result) > 0:
            return result[0]["totalHPBP"]
        else:
            return 0
    except Exception as e:
        logger.warning(f"Error calculating HPBP from exchange, using default: {e}")
        return 25  # Default value

async def calculate_points_from_vault(guild_id):
    """Calculate community points added from vault (inflation)"""
    db = await get_database()
    
    try:
        pipeline = [
            {"$match": {"guildId": guild_id, "type": "vault_addition"}},
            {"$group": {"_id": None, "totalPoints": {"$sum": "$amount"}}}
        ]
        
        cursor = db.point_transactions.aggregate(pipeline)
        result = await cursor.to_list(length=None)
        
        if result and len(result) > 0:
            return result[0]["totalPoints"]
        else:
            return 0
    except Exception as e:
        logger.warning(f"Error calculating points from vault, using default: {e}")
        return 10  # Default value
from pymongo.asynchronous.database import AsyncCollection, AsyncDatabase

from config import AWAIZ_USER_ID
from kusogaki_bot.core.db import MongoDatabase


class FoodCounterRepository:
    """Repository class for food counter persistence"""

    db: AsyncDatabase = None
    food_counter_collection: AsyncCollection = None

    def __init__(self):
        """Initialize database connection"""
        self.db = MongoDatabase.get_db()
        self.food_counter_collection = self.db['food-counters']

    async def get_counter(self) -> int:
        """
        Get a awaiz's food counter from the database

        Args:
            user_id (str): Discord user ID

        Returns:
            int: The current food counter
        """

        food_counter_item: AsyncCollection = await self.food_counter_collection.find_one()

        return food_counter_item.get('count', 0)

    async def inc_counter(self) -> int:
        """
        Save a food counter to the database

        Args:
            counter (FoodCounter): Counter to save

        Returns:
            new_count (int) : New Counter value after the increment
        """

        query = {'user_id': AWAIZ_USER_ID}

        update = {'$inc': {'count': 1}}

        await self.food_counter_collection.update_one(query, update)

        return await self.get_counter()

    async def save_counter(self, counter: int) -> None:
        """
        Save a food counter to the database

        Args:
            counter (FoodCounter): Counter to save
        """

        query = {'user_id': AWAIZ_USER_ID}

        update = {'$inc': {'count': 1}}

        await self.food_counter_collection.update_one(query, update)

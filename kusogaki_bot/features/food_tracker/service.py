from kusogaki_bot.features.food_tracker.data import (
    FoodCounterRepository,
)


class FoodCounterService:
    """Service layer for handling food counter business logic"""

    def __init__(self):
        self.counter_repository = FoodCounterRepository()
        self._food_items = None

    @property
    def food_items(self) -> list[str]:
        """Cached list of food items to check"""

        if self._food_items is None:
            self._food_items = self.mention_repository.get_all_food_items()
        return self._food_items

    async def increment_counter(self) -> int:
        """
        Increment food counter for a user and return new count

        Args:
            user_id (str): Discord user ID

        Returns:
            int: Updated count
        """

        return await self.counter_repository.inc_counter()

    async def get_count(self, user_id: str) -> int:
        """
        Get current count for a user

        Args:
            user_id (str): Discord user ID

        Returns:
            int: Current count
        """
        return await self.counter_repository.get_counter()

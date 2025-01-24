import logging
import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from kusogaki_bot.core import Database

Base = declarative_base()


class FoodCounter(Base):
    """Database model for food counter"""

    __tablename__ = (
        'food_counters_dev'
        if os.getenv('BOT_ENV', 'development') == 'development'
        else 'food_counters'
    )

    user_id = Column(String, primary_key=True)
    count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    def increment(self) -> int:
        """Increment counter and update timestamp"""
        self.count += 1
        self.last_updated = datetime.now()
        return self.count


class FoodCounterRepository:
    """Repository class for food counter persistence"""

    def __init__(self):
        """Initialize database connection"""
        self.db = Database.get_instance()

    def get_counter(self, user_id: str) -> FoodCounter:
        """
        Get a user's food counter from the database

        Args:
            user_id (str): Discord user ID

        Returns:
            FoodCounter: Counter object (new if not found)
        """
        try:
            counter = self.db.query(FoodCounter).filter_by(user_id=user_id).first()
            if not counter:
                counter = FoodCounter(user_id=user_id, count=0)
            return counter
        except SQLAlchemyError as e:
            logging.error(f'Error loading food counter: {str(e)}')
            return FoodCounter(user_id=user_id, count=0)

    def save_counter(self, counter: FoodCounter) -> None:
        """
        Save a food counter to the database

        Args:
            counter (FoodCounter): Counter to save
        """
        try:
            if counter.count > 0:
                if (
                    not self.db.query(FoodCounter)
                    .filter_by(user_id=counter.user_id)
                    .first()
                ):
                    self.db.add(counter)
                self.db.commit()
            else:
                self.db.query(FoodCounter).filter_by(user_id=counter.user_id).delete()
                self.db.commit()
        except SQLAlchemyError as e:
            logging.error(f'Error saving food counter: {str(e)}')
            self.db.rollback()

    def clear_all(self) -> None:
        """Clear all food counters (for testing)"""
        try:
            self.db.query(FoodCounter).delete()
            self.db.commit()
        except SQLAlchemyError as e:
            logging.error(f'Error clearing food counters: {str(e)}')
            self.db.rollback()


class FoodMention(Base):
    """Database model for tracked food words"""

    __tablename__ = 'food_mentions'

    id = Column(Integer, primary_key=True)
    food_item = Column(String, nullable=False)


class FoodMentionRepository:
    """Repository class for food mentions"""

    def __init__(self):
        """Initialize database connection"""
        self.db = Database.get_instance()

    def get_all_food_items(self) -> list[str]:
        """
        Get all food items from the database

        Returns:
            list[str]: List of food items to track
        """
        try:
            mentions = self.db.query(FoodMention).all()
            return [mention.food_item.lower() for mention in mentions]
        except SQLAlchemyError as e:
            logging.error(f'Error loading food mentions: {str(e)}')
            return []

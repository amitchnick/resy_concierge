import logging
import sys

from datetime import datetime, timedelta

def get_logger(name: str):
    root = logging.getLogger(name=name)
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return root

def extract_time_from_token(token: str):
    """extract time from token that looks like: 
    rgs://resy/2/1843946/2/2022-12-18/2022-12-18/20:15:00/2/Indoor Dining"""
    
    split_token = token.split('/')
    return split_token[-3]

def get_next_booking_time(time_to_book: str) -> datetime:
    hour, minute = time_to_book.split(":")
    now = datetime.now()
    next_time_to_book = datetime(now.year, now.month, now.day, hour=int(hour), minute=int(minute), second=0, microsecond=0)
    if now > next_time_to_book:
        next_time_to_book += timedelta(days=1)
    return next_time_to_book
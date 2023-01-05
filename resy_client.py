from typing import List
import json

import requests
from urllib import parse
from constants import RESY_URL
from datetime import datetime, timedelta

from utils import get_logger, extract_time_from_token

LOGGER = get_logger(__name__)

class ResyAPI():
    def __init__(self, user_email: str, user_password: str, api_key: str):
        self.user_email = user_email
        self.user_password = user_password
        self.api_key = api_key
        
        self.auth_token = None

    def authenticate(self) -> str:
        """fetch auth token"""
        response = requests.post(parse.urljoin(RESY_URL, f"3/auth/password"), 
                            data={"email": self.user_email,
                                "password": self.user_password},
        headers={"Authorization": f'ResyAPI api_key="{self.api_key}"'})
        self.auth_token = response.json()["token"]
    
    def _find(self, venue_id: int, 
                        party_size: int, 
                        date: str,
                        num_retries: int = 3):
            find_url = parse.urljoin(RESY_URL, f"4/find")
            try:
                response = requests.get(find_url, 
                        params={"lat": 0, 
                                "long": 0, 
                                "day": date, 
                                "party_size": party_size, 
                                "venue_id": venue_id
                                },
                        headers=self.format_headers())
                slots = response.json()["results"]["venues"][0]["slots"]
                return slots
            except Exception:
                if num_retries:
                    self._find(venue_id, party_size, date, num_retries-1)
    
    def find_reservations(self, 
                        venue_id: int, 
                        party_size: int, 
                        date: str,
                        retry_seconds: int = 10) -> List[str]:
        """Returns list of reservation tokens for available slots"""
        retry_until = datetime.now() + timedelta(seconds=retry_seconds)     
        num_tries = 1
        while datetime.now() < retry_until:
            LOGGER.info(f"Attempting to find available reservation... Attempt number: {num_tries}")
            slots = self._find(venue_id=venue_id, party_size=party_size, date=date)
            if slots:
                slot_tokens = [s["config"]["token"] for s in slots]
                LOGGER.info(f"Found slots! Num available: {len(slot_tokens)}")
                return slot_tokens
            num_tries += 1
        return []
    
    def _get_booking_token_and_payment(self, config_id: str, date: str, party_size: int):
        details_url = parse.urljoin(RESY_URL, f"3/details")
        response = requests.get(details_url, 
                    params={"config_id": config_id, 
                            "day": date, 
                            "party_size": party_size, 
                            },
                    headers=self.format_headers())
        details = response.json()
        book_token = details["book_token"]["value"]
        default_payment_id = details["user"]["payment_methods"][0]["id"]
        return book_token, default_payment_id

    def _book(self, book_token: str, payment_id: int):
        booking_url = parse.urljoin(RESY_URL, f"3/book")
        struct_payment_method = {"id": payment_id}
        response = requests.post(booking_url, 
                    data={"book_token": book_token, "struct_payment_method": json.dumps(struct_payment_method)},
                    headers=self.format_headers())
        return response.json()

    def book_reservation(self, 
                        times: List[str],
                        venue_id: int, 
                        party_size: int, 
                        date: str,):
        res_config_ids = self.find_reservations(venue_id=venue_id, party_size=party_size, date=date)
        time_to_token = {extract_time_from_token(config_id): config_id for config_id in res_config_ids}
        for time in times:
            if time_to_token.get(time): 
                try:
                    LOGGER.info(f"Attempting secure booking token for time {time}.")
                    book_token, payment_id = self._get_booking_token_and_payment(config_id=time_to_token[time], 
                                        date=date, 
                                        party_size=party_size)
                    LOGGER.info("Trying to book...")
                    booking_response = self._book(book_token=book_token, payment_id=payment_id)
                    if booking_response.get('resy_token'):
                        return booking_response # return response if it was a success, otherwise try the next time
                except Exception:
                    continue
        LOGGER.info(f"Could not book times requested. Times available: {list(time_to_token.keys())}")
        return False

    def format_headers(self):
        return {
            "Authorization": f'ResyAPI api_key="{self.api_key}"',
            "x-resy-auth-token": self.auth_token
        }
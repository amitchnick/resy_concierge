from typing import List

import requests
from urllib import parse
from constants import RESY_URL

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
                        date: str,):
            find_url = parse.urljoin(RESY_URL, f"4/find")
            response = requests.get(find_url, 
                        params={"lat": 0, 
                                "long": 0, 
                                "day": date, 
                                "party_size": party_size, 
                                "venue_id": venue_id
                                },
                        headers=self.format_headers())
            return response.json()["results"]["venues"][0]["slots"]
    
    def find_reservations(self, 
                        venue_id: int, 
                        party_size: int, 
                        date: str,
                        num_retries: int = 5) -> List[str]:
        """Returns list of reservation tokens for available slots"""
               
        retries_remaining = num_retries
        while retries_remaining:
            LOGGER.info(f"Attempting to find available reservation. Attempt number: {num_retries - retries_remaining}")
            slots = self._find(venue_id=venue_id, party_size=party_size, date=date)
            if slots:
                slot_tokens = [s["config"]["token"] for s in slots]
                LOGGER.info(f"Found slots! Num available: {len(slot_tokens)}")
                return slot_tokens
            retries_remaining-=1
        return []
    
    def _get_booking_token(self, config_id: str, date: str, party_size: int):
        details_url = parse.urljoin(RESY_URL, f"3/details")
        response = requests.get(details_url, 
                    params={"config_id": config_id, 
                            "day": date, 
                            "party_size": party_size, 
                            },
                    headers=self.format_headers())
        details = response.json()
        return details["book_token"]["value"]

    def _book(self, book_token: str):
        booking_url = parse.urljoin(RESY_URL, f"3/book")
        response = requests.post(booking_url, 
                    data={"book_token": book_token},
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
                    book_token = self._get_booking_token(config_id=time_to_token[time], 
                                           date=date, 
                                           party_size=party_size)
                    
                    return self._book(book_token=book_token)
                except Exception:
                    continue
        raise ValueError("Could not book reservation, none of the desired times are available.")

    def format_headers(self):
        return {
            "Authorization": f'ResyAPI api_key="{self.api_key}"',
            "x-resy-auth-token": self.auth_token
        }
from concurrent.futures import ThreadPoolExecutor
from typing import List
import json

import requests
from urllib import parse
from constants import RESY_URL
from datetime import datetime, timedelta

from tenacity import retry, retry_if_result, stop_after_attempt, stop_after_delay

from utils import get_logger, get_times_to_tokens

LOGGER = get_logger(__name__)

class ResyAPI():
    def __init__(self, user_email: str, user_password: str, api_key: str):
        self.user_email = user_email
        self.user_password = user_password
        self.api_key = api_key
        
        self.auth_token = None

    @retry(stop=stop_after_attempt(10))
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
    
    def _no_slots(slots: List[str]):
        return not bool(slots)
    
    def _return_last_state(retry_state):
        return retry_state.outcome.result()

    @retry(stop=stop_after_delay(10), retry=retry_if_result(_no_slots), retry_error_callback=_return_last_state)
    def find_reservations(self, 
                        venue_id: int, 
                        party_size: int, 
                        date: str) -> List[str]:
        """Returns list of reservation tokens for available slots"""
        LOGGER.info(f"Attempting to find available reservation...")
        slots = self._find(venue_id=venue_id, party_size=party_size, date=date)
        slot_tokens = [s["config"]["token"] for s in slots]
        LOGGER.info(f"Found {len(slots)} available slots.")
        return slot_tokens
    
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

    def _book(self, book_token: str, payment_id: int, retry_seconds: int = 2):
        booking_url = parse.urljoin(RESY_URL, f"3/book")
        struct_payment_method = {"id": payment_id}
        retry_until = datetime.now() + timedelta(seconds=retry_seconds)
        num_tries = 1
        booking_response = {}
        while datetime.now() < retry_until:
            LOGGER.info(f"Attempting to secure booking... Attempt number: {num_tries}")
            response = requests.post(booking_url, 
                    data={"book_token": book_token, "struct_payment_method": json.dumps(struct_payment_method)},
                    headers=self.format_headers())
            booking_response = response.json()
            if booking_response.get('resy_token'):
                return booking_response # return response if it was a success, otherwise retry
            num_tries += 1
        return booking_response

    def secure_booking(self, time: str, config_id: str, date: str, party_size: int):
        LOGGER.info(f"Attempting secure booking token for time {time}.")
        book_token, payment_id = self._get_booking_token_and_payment(config_id=config_id, 
                            date=date, 
                            party_size=party_size)
        LOGGER.info("Received token. Trying to book.")
        booking_response = self._book(book_token=book_token, payment_id=payment_id)
        return booking_response.get('resy_token')

    def book_reservation_multithreaded(self, 
                        times: List[str],
                        venue_id: int, 
                        party_size: int, 
                        date: str,
                        indoor_only: bool = False):
        res_config_ids = self.find_reservations(venue_id=venue_id, party_size=party_size, date=date)
        time_to_token = get_times_to_tokens(res_config_ids, indoor_only=indoor_only)
        results = {}
        with ThreadPoolExecutor(max_workers=len(times)) as executer:
            for t in times:
                if time_to_token.get(t):
                    results[t] = executer.submit(self.secure_booking, t, time_to_token[t], date, party_size)
        reservations_acquired = []
        for t, future in results.items():
            token = future.result()
            if token:
                reservations_acquired.append(t)
        
        if reservations_acquired:
            LOGGER.info(f"Reservation(s) booked! Times: {reservations_acquired}")
        else:
            LOGGER.info(f"Could not book times requested. Times available upon querying: {list(time_to_token.keys())}")
        return reservations_acquired

    def format_headers(self):
        return {
            "Authorization": f'ResyAPI api_key="{self.api_key}"',
            "x-resy-auth-token": self.auth_token
        }
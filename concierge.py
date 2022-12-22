import argparse

from resy_client import ResyAPI

from datetime import datetime
import utils
import time

LOGGER = utils.get_logger(__name__)

# TODO add type of res option
def parse_args():
    parser = argparse.ArgumentParser(description="Concierge bot for booking reservations on Resy.")
    
    parser.add_argument('--email', type=str, required=True, help='Resy account email')
    parser.add_argument('--password', type=str, required=True, help='Resy account password')
    parser.add_argument('--api-key', type=str, required=True, help='Resy account API key')
    parser.add_argument('--times', type=str, required=True, nargs='+', help='Reservation times, ordered by preference')
    parser.add_argument('--date', type=str, required=True, help='Date of reservation')
    parser.add_argument('--party-size', type=str, required=True, help='Reservation party size')
    parser.add_argument('--venue-id', type=int, required=True, help='Venue ID for restaurant where reservation should be made')
    parser.add_argument('--time-to-book', type=str, help="Time that the reservations come out")
    return parser.parse_args()


def main():
    args = parse_args()
    hour, minute = args.time_to_book.split(":")
    res = ResyAPI(user_email=args.email, user_password=args.password, api_key=args.api_key)
    res.authenticate()
    
    while True:
        now = datetime.now()
        if now.hour == int(hour) and now.minute == int(minute):
            start = time.time()
            LOGGER.info(f"Attempting to swipe reservation with parameters: Date: {args.date}, Times: {args.times}, Party Size: {args.party_size}")
            successful_booking = res.book_reservation(venue_id=args.venue_id, party_size=args.party_size, date=args.date, times=args.times)
            end = time.time()
            LOGGER.info(f"Total time to swipe reservation: {end - start} seconds")
            LOGGER.info(f"Booking was a success! Reservation info: {successful_booking}")
            break

if __name__ == "__main__":
    main()
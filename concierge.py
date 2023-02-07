import argparse

from resy_client import ResyAPI

from datetime import datetime, timedelta
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
    parser.add_argument('--time-to-book', type=str, required=True, help="Time that the reservations come out")
    parser.add_argument('--indoor-only', type=bool, help="If True, filter for only indoor reservations", action=argparse.BooleanOptionalAction)
    return parser.parse_args()


def main():
    args = parse_args()
    time_to_book = utils.get_next_booking_time(args.time_to_book) - timedelta(milliseconds=250)
    res = ResyAPI(user_email=args.email, user_password=args.password, api_key=args.api_key)
    res.authenticate()
    LOGGER.info("Sleeping until it's time to book")
    time.sleep(time_to_book.timestamp() - datetime.now().timestamp())
    start = time.time()
    LOGGER.info(f"Time to book! Attempting to swipe reservation with parameters: Date: {args.date}, Times: {args.times}, Party Size: {args.party_size}")
    successful_bookings = res.book_reservation_multithreaded(venue_id=args.venue_id, party_size=args.party_size, date=args.date, times=args.times, indoor_only=args.indoor_only)
    if successful_bookings:
        end = time.time()
        LOGGER.info(f"Total time to swipe reservation: {end - start} seconds")
        LOGGER.info(f"Booking was a success! Reservation times: {successful_bookings}")
    else:
        LOGGER.info("Failed to book reservation in time :(")

if __name__ == "__main__":
    main()

import argparse
from typing import Dict

from resy_client import ResyAPI

from datetime import datetime, timedelta
import utils
import time

from matplotlib import pyplot as plt
from concurrent.futures import ThreadPoolExecutor, Future

LOGGER = utils.get_logger(__name__)

# TODO add type of res option
def parse_args():
    parser = argparse.ArgumentParser(description="Script to plot time vs. available number of slots.")
    
    parser.add_argument('--email', type=str, required=True, help='Resy account email')
    parser.add_argument('--password', type=str, required=True, help='Resy account password')
    parser.add_argument('--api-key', type=str, required=True, help='Resy account API key')
    parser.add_argument('--date', type=str, required=True, help='Date of reservation')
    parser.add_argument('--party-size', type=str, required=True, help='Reservation party size')
    parser.add_argument('--venue-id', type=int, required=True, help='Venue ID for restaurant where reservation should be made')
    parser.add_argument('--time-to-book', type=str, help="Time that the reservations come out")
    return parser.parse_args()

def wait_and_find_slots(booking_time: datetime, venue_id: int, party_size: int, date: str, resy_client: ResyAPI):
    LOGGER.info(f"Sleeping until booking time: {booking_time}")
    time.sleep(booking_time.timestamp() - datetime.now().timestamp())
    LOGGER.info(f"Time to find slots! Attempting to swipe reservation with parameters: Date: {date}, Party Size: {party_size}")
    return resy_client.find_reservations(venue_id, party_size, date)
    

def plot_slots(results: Dict[datetime, Future], fig_name: str):
    x = []
    y = []
    for t, future in results.items():
        slots = future.result()
        LOGGER.info(f"Launching at time {t} got slots {slots}")
        x.append(t.timestamp())
        y.append(len(slots))
    plt.scatter(x, y)
    plt.savefig(fig_name)

def main():
    args = parse_args()
    base_booking_time = utils.get_next_booking_time(args.time_to_book) - timedelta(seconds=1)
    booking_times = [base_booking_time - timedelta(milliseconds=x) for x in range(1000, 0, -10)]
    res = ResyAPI(user_email=args.email, user_password=args.password, api_key=args.api_key)
    res.authenticate()
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executer:
        for t in booking_times:
            results[t] = executer.submit(wait_and_find_slots, t, args.venue_id, args.party_size, args.date, res)
    plot_slots(results=results, fig_name=f"{args.venue_id}_{args.date}.png")



if __name__ == "__main__":
    main()
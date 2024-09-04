from datetime import datetime, timedelta
import random
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from database import save_flights

load_dotenv()

def random_sleep(min_seconds=1, max_seconds=2):
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_flight_info_for_day(page, target_date, formatted_date):
    # Get the HTML content from the page
    page_html = page.content()
    soup = BeautifulSoup(page_html, 'html.parser')
    flights = []

    target_date_slide = soup.select_one(f'div.swiper-slide[data-date="{target_date}"]')

    if not target_date_slide:
        print(f"No flights found for {target_date}")
        return flights
    
    sold_out = target_date_slide.select_one('div.sold-out')
    flight_rows = target_date_slide.select('label.flight_info_content')

    for flight_row in flight_rows:
        price_div = flight_row.select_one('div.price_content h2')
        departure_time_div = flight_row.select('div.flight_time_content div.time_content h5')

        # Extract price
        price_text = price_div.get_text(strip=True).replace('€', '').replace('EUR', '').replace(',', '.').strip() if price_div else 'N/A'
        
        # If sold out, set price to "Full"
        price = "Full" if sold_out else price_text if price_text != "N/A" else 'N/A'

        # Extract departure and arrival times
        departure_time = departure_time_div[0].get_text(strip=True) if len(departure_time_div) > 0 else 'N/A'
        arrival_time = departure_time_div[1].get_text(strip=True) if len(departure_time_div) > 1 else 'N/A'
        flight_time = f"{departure_time} - {arrival_time}"

        # Flight number
        flight_number = f"{target_date}{departure_time}"
        flights.append({
            'price': price,
            'flight_number': flight_number,
            'time': flight_time,
            'date': formatted_date
        })

    return flights

def run_flyska_ticket_script_180days():
    airport_pairs = [
        ('MLH,BSL', 'PRN'),
        ('PRN', 'DUS'),
        ('PRN', 'MUC'),
        ('DUS', 'PRN'),
        ('PRN', 'STR'),
        ('STR', 'PRN'),
        ('PRN', 'MLH,BSL'),
        ('MUC', 'PRN'),
    ]
    city_to_airport_code = {
        'MLH,BSL': 'BSL',
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Use headless=True for production
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'DNT': '1',
            }
        )
        page = context.new_page()

        for departure, arrival in airport_pairs:
            for day in range(8, 30):
                try:
                    url = 'https://prod.flyksa.com/sq'
                    page.goto(url)
                    random_sleep(1, 2)

                    # Click on the "One Way" option
                    page.click('input#oneWay')

                    page.click('div.from_holder.choose_directions .choices')

                    # Click on the departure option
                    page.click(f'div.choices__item[data-value="{departure}"]')

                    # Select arrival
                    page.click('div.to_holder.choose_directions .choices')
                    page.click(f'div.to_holder div.choices__item[data-value="{arrival}"]', timeout=10000)

                    page.click('#outdate')
                    page.wait_for_timeout(1000)

                    target_date = datetime.now() + timedelta(days=day)
                    target_date_str = target_date.strftime('%Y-%m-%d')
                    database_targetdate = target_date.strftime('%d.%m')

                    target_month = target_date.month
                    target_year = target_date.year
                    target_date_obj = datetime.strptime(target_date_str, '%Y-%m-%d')

                      # Initialize displayed month and year to simulate current display
                    now = datetime.now()
                    displayed_month = now.month
                    displayed_year = now.year
                    while True:
                        # Check if the displayed month and year match the target month and year
                        if displayed_year == target_year and displayed_month == target_month:
                             break
                         
                        # Navigate to the correct month
                        if (displayed_year < target_year) or (displayed_year == target_year and displayed_month < target_month):
                            page.click('button.next-button.unit')
                            displayed_month += 1
                            if displayed_month > 12:
                                displayed_month = 1
                                displayed_year += 1
                                
                    day_selector = f'div.day.unit[data-time="{int(target_date_obj.timestamp()) * 1000}"]'
                    page.click(day_selector)
                    page.wait_for_timeout(1000)

                    # Click the search button        
                    page.click('button:has-text("Kërko fluturim")')

                    random_sleep(3, 6)

                    flights = extract_flight_info_for_day(page, target_date_str,database_targetdate)
                    
                    if flights:
                        for flight in flights:
                        # Prepare the payload for the API call
                            payload = {
                                'date': flight['date'],
                                'time': flight['time'],
                                'flight_number': flight['flight_number'],
                                'price': flight['price']
                            }

                            try:
                                # Send the API call to check existence
                                response = requests.post('http://scrap-dot-flycop-431921.el.r.appspot.com/check-existence', json=payload)
                                response.raise_for_status()  # Raise an exception for HTTP errors

                                if response.status_code == 201 and response.json() is False:
                                    print("about to be saved to the database")
                                    # Save the flight information
                                    original_departure = departure
                                    original_arrival = arrival
                                    departure = city_to_airport_code.get(departure, departure)
                                    arrival = city_to_airport_code.get(arrival, arrival)
                                    save_flights([flight], departure, arrival, database_targetdate, url)
                                    departure = original_departure
                                    arrival = original_arrival
                            except requests.exceptions.RequestException as e:
                                print(f"Request failed: {e}")
                            # Save the flight information
                                save_flights([flight], departure, arrival, flight['date]'], url)

                        
                    else:  
                        print("No flights found for the specified date.")

                except Exception as e:
                    print(f"An error occurred while processing {departure} to {arrival} on day {day}: {e}")
                    continue

        browser.close()

if __name__ == "__main__":
    run_flyska_ticket_script_180days()

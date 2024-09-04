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

def extract_flight_info(page_html, flight_date):
    soup = BeautifulSoup(page_html, 'html.parser')
    flights = []

    flight_rows = soup.select('div.available-flight')
    for flight_row in flight_rows:
        price_div = flight_row.select_one('div.price span.value')
        airline_div = flight_row.select_one('div.flight-nr')
        departure_div = flight_row.select_one('span.departure-time')

        if price_div and airline_div and departure_div:
            flights.append({
                'price': price_div.get_text(strip=True),
                'flight_number': airline_div.get_text(strip=True),
                'time': departure_div.get_text(strip=True),
                'date': flight_date
            })

    return flights

def run_airprishtina_ticket_script():
    airport_pairs = [
        ('Pristina', 'Basel-Mulhouse', True),
        ('Pristina', 'Stuttgart', True),
        ('Pristina', 'Düsseldorf', True),
        ('Pristina', 'München', True),
        ('Pristina', 'Basel-Mulhouse', False),
        ('Pristina', 'Stuttgart', False),
        ('Pristina', 'Düsseldorf', False),
        ('Pristina', 'München', False),
    ]

    city_to_airport_code = {
        'Pristina': 'PRN',
        'Düsseldorf': 'DUS',
        'München': 'MUC',
        'Stuttgart': 'STR',
        'Basel-Mulhouse': 'BSL'
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'DNT': '1',
            }
        )
        page = context.new_page()

        for departure, arrival, reversed in airport_pairs:
            for day in range(0, 8):
                url = 'https://www.airprishtina.com/sq/'
                page.goto(url)
                random_sleep(1)

                # Click on the "One Way" option
                page.click('div.one-way')

                print(f"Checking departure: {departure}")
                page.fill('input#txt_Flight1From', departure)
                page.locator(f'[data-text="{departure}"]').click()
                random_sleep(1)

                # Populate the "To" input field with the arrival location
                page.fill('input#txt_Flight1To', arrival)
                random_sleep(1)
                page.locator(f'[data-text="{arrival}"]').click()
                random_sleep(1)

                if reversed:
                    swap_icon = page.locator('#pnl_Flight1DestinationSwap[data-flight-order="1"] i.fas.fa-sync')
                    swap_icon.click()
                random_sleep(1)
                
                target_date_obj = (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d')
                
                # Click on the date input field to open the date picker
                page.click('#txt_FromDateText')
                random_sleep(1)

                target_date = datetime.now() + timedelta(days=day)
                target_month = target_date.month
                target_year = target_date.year
                
                now = datetime.now()
                displayed_month = now.month
                displayed_year = now.year
                formatted_date = (datetime.now() + timedelta(days=day)).strftime('%d.%m')
                
                while True:
                    if displayed_year == target_year and displayed_month == target_month:
                        break
                     
                    if (displayed_year < target_year) or (displayed_year == target_year and displayed_month < target_month):
                        page.click('th.next.available')
                        displayed_month += 1
                        if displayed_month > 12:
                            displayed_month = 1
                            displayed_year += 1
                            
                # Select the first matching element
                div_elements = page.locator(f'td[data-usr-date="{target_date_obj}"]').all()
                random_sleep(1)

                if div_elements:
                    div_element = div_elements[0]
                    
                    if div_element.is_visible() and div_element.evaluate("element => element.classList.contains('flight-present')"):
                        div_element.click()
                        random_sleep(3)
        
                        # Click the search button
                        search_button_selector = 'button.btn.btn-red.ac-popup'
                        page.click(search_button_selector)
                        random_sleep(5)
        
                        page_html = page.content()
                        flights = extract_flight_info(page_html, formatted_date)
        
                        for flight in flights:
                            # Check if any required field is empty
                            if not all([flight['price'], flight['flight_number'], flight['time'], flight['date']]):
                                continue

                            print(f"Checking existence of flight: {flight['flight_number']} on {flight['date']} at {flight['time']} for {flight['price']}€")
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
                                    original_departure = departure
                                    original_arrival = arrival
                                    departure = city_to_airport_code.get(departure, departure)
                                    arrival = city_to_airport_code.get(arrival, arrival)

                                    # Save the flight information
                                    save_flights([flight], departure, arrival, target_date, url)
                                    departure = original_departure
                                    arrival = original_arrival
                            except requests.exceptions.RequestException as e:
                                print(f"Request failed: {e}")
                                original_departure = departure
                                original_arrival = arrival
                                departure = city_to_airport_code.get(departure, departure)
                                arrival = city_to_airport_code.get(arrival, arrival)

                            # Save the flight information
                                save_flights([flight], departure, arrival, target_date, url)
                                departure = original_departure
                                arrival = original_arrival
                            
                    
                    else:
                        print("Div does not have the 'flight-present' class, skipping the click.")
                else:
                    print(f"No div elements found for date {target_date_obj}")
                 
        browser.close()

if __name__ == "__main__":
    run_airprishtina_ticket_script()

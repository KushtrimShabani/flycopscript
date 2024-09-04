from datetime import datetime, timedelta
import json
import os
import random
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from database import save_flights

load_dotenv()

def random_sleep(min_seconds=1, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_flight_info(page_html):
    soup = BeautifulSoup(page_html, 'html.parser')
    flights = []

    # Select all rows in the table
    rows = soup.select('table.flug_auswahl tbody tr')
    print(f"Found {len(rows)} rows in the flight table.")

    for row in rows:
        date_cell = row.select_one('td.ab_datum')
        if date_cell:
            flight_date = date_cell.get_text(strip=True)
            print(f"Checking flight date: {flight_date}")
            flight_date_part = flight_date.split(' ')[1]

            time_cell = row.select_one('td.ab_an')
            flight_number_cell = row.select_one('td.carrier_flugnr')
            price_cell = row.select_one('td.b_ges_preis')

            price_text = price_cell.get_text(strip=True) if price_cell else 'N/A'
            price_text = price_text.replace('€', '').replace(',', '.').strip()
            if price_text.lower() == 'sold out':
                price = 'N/A'
            else:
                price = price_text if price_text != 'N/A' else 'N/A'

            flight = {
                'date': flight_date_part,
                'time': time_cell.get_text(strip=True) if time_cell else 'N/A',
                'flight_number': flight_number_cell.get_text(strip=True) if flight_number_cell else 'N/A',
                'price': price
            }
            flights.append(flight)
    
    return flights

def run_flyrbp_ticket_script_180days():
    airport_pairs = [
        ('MLH', 'PRN'),
        ('PRN', 'DUS'),
        ('PRN', 'MUC'),
        ('DUS', 'PRN'),
        ('PRN', 'STR'),
        ('STR', 'PRN'),
        ('PRN', 'MLH'),
        ('MUC', 'PRN'),
        ('PRN', 'NUE'),
        ('NUE', 'PRN'),
    ]
    city_to_airport_code = {
        'MLH': 'BSL',
    }

    with sync_playwright() as p:
           browser = p.chromium.launch(headless=True)  # Set to True to run headlessly
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
                 for day in range(40, 180 , 26):
                     
            
                         url = 'https://www.flyrbp.com'
                         page.goto(url)
                         random_sleep(2, 3)
            
                         # Click the "Njëdrejtimshe" (one-way) radio button
                         page.click('input[value="ow"]')
            
                         # Select the "Nisja nga" (Departure from) dropdown
                         page.select_option('select[name="VON"]', value=departure)
            
                         # Select the "Kthimi" (Return to) dropdown
                         page.select_option('select[name="NACH"]', value=arrival)
            
                         # Set the departure date to the calculated date
                         target_date_year = (datetime.now() + timedelta(days=day)).strftime('%d.%m.%Y')
                         target_date = (datetime.now() + timedelta(days=day)).strftime('%d.%m')
                         page.fill('input[name="DATUM_HIN"]', target_date_year)
            
                         # Click the search button
                         page.click('a.book-home')
                         random_sleep(2, 3)
            
                         page_html = page.content()
                         flights = extract_flight_info(page_html)
                         if flights:
                            print("Flight information extracted:")
                            for flight in flights:
                            # Prepare the payload for the API call
                                payload = {
                                'date': flight['date'],
                                'time': flight['time'],
                                'flight_number': flight['flight_number'],
                                'price': flight['price']
                                }

                                # Send the API call to check existence
                                response = requests.post('http://scrap-dot-flycop-431921.el.r.appspot.com/check-existence', json=payload)
                                if response.status_code == 201 and response.json() is False:
                        
                                     departure_code = city_to_airport_code.get(departure, departure)
                                     arrival_code = city_to_airport_code.get(arrival, arrival)

                                 # Save the flight information
                                     save_flights([flight], departure_code, arrival_code, target_date, url)
                                     continue
                    
                         else:  
                            print("No flights found for the specified date.")

           browser.close()
    return {"status": "success", "message": "Flyrbp ticket script executed"}

if __name__ == "__main__":
    run_flyrbp_ticket_script_180days()

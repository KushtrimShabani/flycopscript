from datetime import datetime, timedelta
import psycopg2
import random
import subprocess
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from database import save_flights

load_dotenv()

DATABASE_URL = "dbname=flycop user=flycop host=104.199.31.112 password=flycop port=5432" 

def save_flights(flights, from_location, to_location, day, url):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id SERIAL PRIMARY KEY,
            date TEXT,
            time TEXT,
            flight_number TEXT,
            price TEXT,
            from_location TEXT,
            to_location TEXT,
            created_at TIMESTAMP,
            website TEXT
        )
    ''')

    for flight in flights:
        price = flight['price'] if flight['price'] is not None else 'N/A'
        cursor.execute('''
            INSERT INTO flights (date, time, flight_number, price, from_location, to_location, created_at, website)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            flight['date'],
            flight['time'],
            flight['flight_number'],
            price,
            from_location,
            to_location,
            datetime.now(),
            url
        ))

    conn.commit()
    conn.close()

def random_sleep(min_seconds=1, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_flight_info(page_html, target_date):
    soup = BeautifulSoup(page_html, 'html.parser')
    flights = []

    # Select all rows in the table
    rows = soup.select('table.flug_auswahl tbody tr')
    print(f"Found {len(rows)} rows in the flight table.")

    for row in rows:
        # Extract date from the row
        date_cell = row.select_one('td.ab_datum')
        if date_cell:
            flight_date = date_cell.get_text(strip=True)
            flight_date_part = flight_date.split(' ')[1]  # Assuming the date is the second part
            current_year = datetime.now().year
            flight_date_formatted = flight_date_part

            # Check if this is the desired date
            print(f"Flight date: {flight_date}")
            # Extract flight details
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
                'date': flight_date_formatted,
                'time': time_cell.get_text(strip=True) if time_cell else 'N/A',
                'flight_number': flight_number_cell.get_text(strip=True) if flight_number_cell else 'N/A',
                'price': price
            }
            flights.append(flight)
    
    return flights

def run_prishtina_ticket_script():
    airport_pairs = [
        ('Prishtina (PRN)', 'Düsseldorf (DUS)'),
        ('Prishtina (PRN)', 'München (MUC)'),
        ('Düsseldorf (DUS)', 'Prishtina (PRN)'),
        ('München (MUC)', 'Prishtina (PRN)'),
        ('Prishtina (PRN)', 'Nürnberg (NUE)'),
        ('Prishtina (PRN)', 'Stuttgart (STR)'),
        ('Prishtina (PRN)', 'Basel/Mulhouse (MLH)'),
        ('Basel/Mulhouse (MLH)', 'Prishtina (PRN)'),
        ('Nürnberg (NUE)', 'Prishtina (PRN)'),
        ('Stuttgart (STR)', 'Prishtina (PRN)')
    ]
    city_to_airport_code = {
        'Prishtina (PRN)': 'PRN',
        'Düsseldorf (DUS)': 'DUS',
        'München (MUC)': 'MUC',
        'Nürnberg (NUE)': 'NUE',
        'Stuttgart (STR)': 'STR',
        'Basel/Mulhouse (MLH)':'BSL'
    }

    for departure, arrival in airport_pairs:
        for day in range(0, 2):
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
                url = 'https://www.prishtinaticket.net'
                page.goto(url)
                random_sleep(2, 3)
                page.click('input[value="ow"]')

                # Select the "Nisja nga" (Departure from) dropdown
                page.select_option('select[name="VON"]', value=departure)

                # Select the "Kthimi" (Return to) dropdown
                page.select_option('select[name="NACH"]', value=arrival)

                # Set the departure date
                target_date = (datetime.now() + timedelta(days=day)).strftime('%d.%m.%Y')
                page.fill('input[name="DATUM_HIN"]', target_date)

                # Click the search button
                page.click('a.book-home')
                random_sleep(3, 6)

                page_html = page.content()
                flights = extract_flight_info(page_html, target_date)

                for flight in flights:
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
                    print("No flights found for the specified date.")
                browser.close()
    
    return {"status": "success", "message": "Prishtina ticket script executed"}

# You can still call main() directly for standalone script execution
if __name__ == "__main__":
    run_prishtina_ticket_script()

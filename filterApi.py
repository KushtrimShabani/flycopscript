from datetime import datetime, timedelta
from flask_cors import CORS
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import psycopg2
import time
from flask import Flask, jsonify, request
import logging
# from airpristina import run_airprishtina_ticket_script
from airprishtina180days import run_airprishtina_ticket_script_180days
from airprishtina30days import run_airprishtina_ticket_script_30days
from airpristina import run_airprishtina_ticket_script
from ark import run_arkpy_ticket_script
from ark30days import run_arkpy_ticket_script_30days
from flyska import run_flyska_ticket_script
from flyska180days import run_flyska_ticket_script_180days
from flyska30days import run_flyska_ticket_script_30days
from kosfly import run_kosfly_ticket_script
from kosfly180days import run_kosfly_ticket_script_180days
from kosfly30days import run_kosfly_ticket_script_30days
from prishtinaticket import run_prishtina_ticket_script
from prishtinaticket180days import run_prishtina_ticket_script_180days
from prishtinaticket30days import run_prishtina_ticket_script_30days
from rfly import run_flyrbp_ticket_script
from rfly180days import run_flyrbp_ticket_script_180days
from rfly30days import run_flyrbp_ticket_script_30days


logging.basicConfig(level=logging.INFO)

def run_script_in_thread(script):
    try:
        logging.info(f"Starting script: {script.__name__}")
        script()
        logging.info(f"Finished script: {script.__name__}")
    except Exception as e:
        logging.error(f"Error running script {script.__name__}: {str(e)}")


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
DATABASE_URL = "dbname=flycop user=flycop host=104.199.31.112 password=flycop port=5432" 

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Database connection successful!")
    conn.close()
except Exception as e:
    print(f"Database connection failed: {e}")

@app.route('/')
def index():
    return f'DATABASE_URL is: {DATABASE_URL}'

def query_db(query, args=(), one=False):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(query, args)
        columns = [desc[0] for desc in cursor.description]
        rv = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        return {'error': str(e)}

def run_script_in_thread(script):
    try:
        script()
    except Exception as e:
        print(f"Error running script {script.__name__}: {e}")

@app.route('/script', methods=['GET'])
def run_scripts():
    try:
        # List of script functions to run
        scripts = [
            run_prishtina_ticket_script,
            run_flyska_ticket_script,
            run_kosfly_ticket_script,
            run_arkpy_ticket_script,
            run_flyrbp_ticket_script,
            run_airprishtina_ticket_script
        ]

        # Use ThreadPoolExecutor to run multiple scripts concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:  # Adjust max_workers as needed
            for script in scripts:
                executor.submit(run_script_in_thread, script)

        # Immediately return a successful response
        return jsonify({'message': 'Scripts initiated'}), 200
    except Exception as e:
        # Ensure the route still returns a successful status code even if an exception occurs
        print(f"Exception occurred: {e}")
        return jsonify({'message': 'Scripts initiated'}), 200

@app.route('/script-30days', methods=['GET'])
def run_scripts_30days():
    try:
        # List of script functions to run
        scripts = [
            run_prishtina_ticket_script_30days,
            run_flyska_ticket_script_30days,
            run_kosfly_ticket_script_30days,
            run_arkpy_ticket_script_30days,
            run_flyrbp_ticket_script_30days,
            run_airprishtina_ticket_script_30days
        ]

        # Use ThreadPoolExecutor to run multiple scripts concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:  # Adjust max_workers as needed
            for script in scripts:
                executor.submit(run_script_in_thread, script)

        # Immediately return a successful response
        return jsonify({'message': 'Scripts initiated'}), 200
    except Exception as e:
        # Ensure the route still returns a successful status code even if an exception occurs
        print(f"Exception occurred: {e}")
        return jsonify({'message': 'Scripts initiated'}), 200

@app.route('/script-180days', methods=['GET'])
def run_scripts_180days():
    try:
        # List of script functions to run
        scripts = [
            run_prishtina_ticket_script_180days,
            run_flyrbp_ticket_script_180days,
            run_kosfly_ticket_script_180days,
            run_flyska_ticket_script_180days,
            run_arkpy_ticket_script_30days,
            run_airprishtina_ticket_script_180days
        ]

        # Use ThreadPoolExecutor to run multiple scripts concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:  # Adjust max_workers as needed
            for script in scripts:
                executor.submit(run_script_in_thread, script)

        # Immediately return a successful response
        return jsonify({'message': 'Scripts initiated'}), 200
    except Exception as e:
        # Ensure the route still returns a successful status code even if an exception occurs
        print(f"Exception occurred: {e}")
        return jsonify({'message': 'Scripts initiated'}), 200

@app.route('/fetch-price-differences', methods=['GET'])
def fetch_price_differences():
    query = '''
    SELECT
        id,
        date,
        time,
        flight_number,
        price,
        from_location,
        to_location,
        created_at,
        website
    FROM
        flights
    ORDER BY
        flight_number,
        date,
        website,
        created_at DESC;
    '''

    records = query_db(query)
    print(f"Records: {records}")  # Debugging line to check the fetched records
    # Process records to find price differences
    flight_data = {}
    results = []

    for record in records:
        key = (record['flight_number'], record['date'], record['website'])
        # if key not in flight_data:
        #     flight_data[key] = []
        
        flight_data[key].append(record)

    for key, records in flight_data.items():
        if len(records) > 1:
            # Sort records by created_at in descending order
            records.sort(key=lambda x: x['created_at'], reverse=True)
            
            new_price_record = records[0]
            previous_price_record = records[1]
            
            if new_price_record['price'] != previous_price_record['price']:
                results.append({
                    'id': new_price_record['id'],
                    'date': new_price_record['date'],
                    'flight_number': new_price_record['flight_number'],
                    'new_price': new_price_record['price'],
                    'previous_price': previous_price_record['price'],
                    'website': new_price_record['website'],
                    'created_at': new_price_record['created_at']
                })

    return jsonify(results)

@app.route('/flights', methods=['GET'])
def get_all_flights():
    try:
        flights = query_db('SELECT id, date, time, flight_number, price, from_location, to_location, created_at, website FROM flights')
        return jsonify(flights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flights/<date>', methods=['GET'])
def get_flights_by_date(date):
    try:
        flights = query_db('SELECT * FROM flights WHERE date LIKE %s', [f'%{date}'])
        return jsonify(flights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flights/byairline', methods=['GET'])
def filter_flights():
    order = request.args.get('order', type=str)
    query = '''
    SELECT f.id, 
           f.date, 
           f.time, 
           f.flight_number, 
           f.price, 
           f.from_location, 
           f.to_location, 
           f.created_at, 
           f.website,
           (SELECT price 
            FROM flights 
            WHERE flight_number = f.flight_number 
            AND date < f.date 
            ORDER BY date DESC 
            LIMIT 1) AS previous_price
    FROM flights f
    '''
    if order == 'low':
        query += ' ORDER BY CAST(f.price AS FLOAT) ASC NULLS LAST'
    elif order == 'high':
        query += ' ORDER BY CAST(f.price AS FLOAT) DESC NULLS LAST'
    
    try:
        flights = query_db(query)
        return jsonify(flights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flights/order_by_date', methods=['GET'])
def order_flights_by_date():
    order = request.args.get('order', type=str, default='asc')
    query = '''
    SELECT id, 
           price, 
           airline, 
           departure, 
           from_location, 
           to_location, 
           flight_date, 
           created_at, 
           website 
    FROM flights
    '''
    if order == 'asc':
        query += ' ORDER BY flight_date ASC, departure ASC'
    elif order == 'desc':
        query += ' ORDER BY flight_date DESC, departure DESC'
    
    try:
        flights = query_db(query)
        return jsonify(flights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def convert_to_custom_format(date_str):
    # Mapping weekday abbreviations to full names for accurate conversion
    weekday_map = {
        'Mo': 'Monday', 'Di': 'Tuesday', 'Mi': 'Wednesday', 'Do': 'Thursday', 'Fr': 'Friday', 'Sa': 'Saturday', 'So': 'Sunday'
    }
    date_format = '%a %d.%m'
    try:
        # Convert custom date to datetime object
        date_obj = datetime.strptime(date_str, date_format)
        # Return ISO format date string
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        return None

@app.route('/flights/days', methods=['GET']) # Add a new route for filtering flights by day range and location
def filter_flights_day_range():
    try:
        day_range = request.args.get('day_range', type=str)
        from_location = request.args.get('from_location', type=str)
        to_location = request.args.get('to_location', type=str)
        
        if day_range is None:
            day_range = '1-7'
        
        day_ranges = {
            '1-30': (1, 30),
            '1-7': (1, 7),
            '8-14': (8, 14),
            '14-30': (14, 30),
            '30-180': (30, 180),
            '180-360': (180, 360)
        }
        
        start_days, end_days = day_ranges[day_range]
        
        query = '''
        SELECT id, date, time, flight_number, price, from_location, to_location, created_at, website 
        FROM flights 
        WHERE 1=1
        '''
        query_params = []
        
        if start_days is not None and end_days is not None:
            # Adjusting the date format to match '11.08'
            date_format = '%d.%m'
            current_date = datetime.now()
            start_date = current_date + timedelta(days=start_days)
            end_date = current_date + timedelta(days=end_days)
            start_date_str = start_date.strftime(date_format)
            end_date_str = end_date.strftime(date_format)
            
            query += ' AND SUBSTRING(date, 4) >= %s AND SUBSTRING(date, 4) <= %s'
            query_params.extend([start_date_str, end_date_str])
        
        if from_location:
            query += ' AND from_location = %s'
            query_params.append(from_location)
        
        if to_location:
            query += ' AND to_location = %s'
            query_params.append(to_location)
        
        flights = query_db(query, query_params)
        return jsonify(flights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/flights/filter', methods=['GET'])
def filter_flights_day_location():
    try:
        from_location = request.args.get('from_location', type=str)
        to_location = request.args.get('to_location', type=str)
        days = request.args.get('days', type=int)

        # Debugging: print out the parameters received
        print(f"Received parameters: from_location={from_location}, to_location={to_location}, days={days}")

        if days is None or days <= 0:
            return jsonify({'error': 'The days parameter is required and must be greater than 0'}), 400

        query = '''
        SELECT id, date, time, flight_number, price, from_location, to_location, created_at, website 
        FROM flights 
        WHERE 1=1
        '''
        query_params = []

        if from_location:
            query += ' AND from_location = %s'
            query_params.append(from_location)

        if to_location:
            query += ' AND to_location = %s'
            query_params.append(to_location)

        if days:
            # Adjusting the date format to match '11.08'
            date_format = '%d.%m'
            current_date = datetime.now()
            end_date = current_date + timedelta(days=days)
            current_date_str = current_date.strftime(date_format)
            end_date_str = end_date.strftime(date_format)

            query += ' AND SUBSTRING(date, 4) >= %s AND SUBSTRING(date, 4) <= %s'
            query_params.extend([current_date_str, end_date_str])

        # Debugging: print out the final query and params
        print(f"Final query: {query}")
        print(f"Query params: {query_params}")

        flights = query_db(query, query_params)
        return jsonify(flights)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/flights/latest_prices', methods=['GET'])
def get_latest_and_previous_prices():
    try:
        query = '''
        WITH ranked_flights AS (
            SELECT id, date, time, flight_number, price, from_location, to_location, created_at, website,
                   ROW_NUMBER() OVER (PARTITION BY flight_number, website, date, time ORDER BY created_at DESC) AS rn
            FROM flights
        )
        SELECT rf1.id, rf1.date, rf1.time, rf1.flight_number, rf1.price AS latest_price, rf1.from_location, rf1.to_location, rf1.created_at, rf1.website,
               rf2.price AS previous_price
        FROM ranked_flights rf1
        LEFT JOIN ranked_flights rf2
        ON rf1.flight_number = rf2.flight_number
        AND rf1.website = rf2.website
        AND rf1.date = rf2.date
        AND rf1.time = rf2.time
        AND rf1.rn = rf2.rn - 1
        WHERE rf1.rn = 1
        AND rf1.price <> rf2.price
        '''
        print(f"Executing query: {query}")  # Debug statement
        flights = query_db(query)
        print(f"Query result: {flights}")  # Debug statement
        return jsonify(flights)
    except Exception as e:
        print(f"Error: {e}")  # Debug statement
        return jsonify({'error': str(e)}), 500
    
@app.route('/flights/grouped', methods=['GET']) # Add a new route for fetching and grouping flights by website
def get_flights_grouped_by_website():
    try:
        # Construct the SQL query to fetch all flight data and order by website
        query = '''
        SELECT id, date, time, flight_number, price, from_location, to_location, created_at, website 
        FROM flights
        ORDER BY website
        '''
        
        # Execute the query and fetch all results using query_db
        flights = query_db(query)
        
        # Check for errors in the query result
        if 'error' in flights:
            return jsonify(flights), 500
        
        # Debug statement to print the fetched flights
        print(f"Fetched flights: {flights}")
        
        # Group the results by the website field
        grouped_results = {}
        for flight in flights:
            # Debug statement to print each flight dictionary
            print(f"Processing flight: {flight}")
            
            website = flight['website']
            if website not in grouped_results:
                grouped_results[website] = []
            grouped_results[website].append({
                'id': flight['id'],
                'date': flight['date'],
                'time': flight['time'],
                'flight_number': flight['flight_number'],
                'price': flight['price'],
                'from_location': flight['from_location'],
                'to_location': flight['to_location'],
                'created_at': flight['created_at']
            })
        
        # Return the grouped results as a JSON response
        return jsonify(grouped_results)
    
    except Exception as e:
        print(f"Error: {e}")  # Debug statement
        return jsonify({'error': str(e)}), 500

    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

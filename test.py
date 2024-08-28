import requests
import logging
import schedule
import time
from datetime import datetime, timedelta
from twilio.rest import Client
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Twilio credentials
account_sid = 'AC0b3d44dde5d612623b1626ff02c77410'
auth_token = '83dddc46e3623d3b438d1d1c47b8a456'
twilio_phone_number = '+15418349179'

client = Client(account_sid, auth_token)


# Function to get location
def get_location():
    try:
        response = requests.get('https://ipinfo.io')
        data = response.json()
        loc = data['loc'].split(',')
        latitude = float(loc[0])
        longitude = float(loc[1])
        logging.info("Fetched location: Latitude %s, Longitude %s", latitude, longitude)
        return latitude, longitude
    except Exception as e:
        logging.error("Failed to get location: %s", str(e))
        return None, None


# Function to get prayer times
def get_prayer_times(latitude, longitude, timezone):
    logging.info("Fetching prayer times for latitude: %s, longitude: %s, timezone: %s", latitude, longitude, timezone)
    url = f'http://api.aladhan.com/v1/timings?latitude={latitude}&longitude={longitude}&timezonestring={timezone}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 200:
            logging.info("Successfully fetched prayer times.")
            return data['data']['timings']
        else:
            logging.error("Failed to fetch prayer times, API response code: %s", data['code'])
            return None
    else:
        logging.error("Failed to fetch prayer times, HTTP status code: %s", response.status_code)
        return None


# Function to send SMS
def send_sms(to_phone_number, body):
    logging.info("Preparing to send SMS to: %s", to_phone_number)
    try:
        message = client.messages.create(
            body=body,
            from_=twilio_phone_number,
            to=to_phone_number
        )
        logging.info("SMS sent successfully to %s, Message SID: %s", to_phone_number, message.sid)
    except Exception as e:
        logging.error("Failed to send SMS: %s", str(e))


# Function to schedule SMS reminders
def schedule_sms_reminders(prayer_times, phone_numbers, timezone):
    logging.info("Scheduling SMS reminders for the following prayer times: %s", prayer_times)
    iqama_intervals = {
        "Fajr": 30,
        "Dhuhr": 20,
        "Asr": 20,
        "Maghrib": 15,
        "Isha": 25
    }

    for prayer, time_str in prayer_times.items():
        if prayer in iqama_intervals:
            time_obj = datetime.strptime(time_str, "%H:%M").replace(tzinfo=pytz.timezone(timezone))
            schedule_time = time_obj.strftime("%H:%M")

            for phone_number in phone_numbers:
                schedule.every().day.at(schedule_time).do(send_sms, phone_number,
                                                          f"Hurry Up Youssef! The {prayer} time has just started!!")
                logging.info("Scheduled Azan SMS for %s at %s", prayer, schedule_time)

                iqama_time = (time_obj + timedelta(minutes=iqama_intervals[prayer])).strftime("%H:%M")
                schedule.every().day.at(iqama_time).do(send_sms, phone_number, f"The Iqama for {prayer} is STARTING!!")
                logging.info("Scheduled Iqama SMS for %s at %s", prayer, iqama_time)


# Main function to run the script
def main():
    # Get location
    latitude, longitude = get_location()
    if latitude is None or longitude is None:
        logging.error("Exiting script due to failure in fetching location.")
        return

    timezone = "Africa/Cairo"  # Set timezone to Cairo, Egypt

    # Get phone numbers
    phone_numbers = []
    while True:
        phone_number = input("Enter a phone number (with country code, e.g., +201234567890) or press Enter to finish: ")
        if phone_number.strip() == "":
            break
        phone_numbers.append(phone_number.strip())

    if not phone_numbers:
        logging.error("No phone numbers entered. Exiting script.")
        return

    # Fetch prayer times
    prayer_times = get_prayer_times(latitude, longitude, timezone)
    if not prayer_times:
        logging.error("Exiting script due to failure in fetching prayer times.")
        return

    # Remove non-prayer times
    for key in ["Sunrise", "Sunset", "Imsak", "Midnight", "Firstthird", "Lastthird"]:
        prayer_times.pop(key, None)

    # Schedule SMS reminders
    schedule_sms_reminders(prayer_times, phone_numbers, timezone)

    # Run the schedule
    logging.info("Entering the main loop to keep the scheduler running.")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

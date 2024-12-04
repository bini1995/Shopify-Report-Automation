import requests
import pandas as pd
from datetime import date, datetime, timedelta
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import schedule
import time
import pytz  # To handle time zones
import boto3
from botocore.exceptions import NoCredentialsError
import logging
from collections import defaultdict

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv("/Users/bini.taddesse@vydia.com/Desktop/Production Shopify Report Automation/.env")

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# AWS Credentials
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
***REMOVED***_KEY = os.getenv("***REMOVED***_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = "shopify-report-automation"

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=***REMOVED***_KEY,
    region_name=AWS_REGION
)

# Shopify Configuration
SHOP_NAME = "shop-vydia"
***REMOVED***

# Stakeholders
STAKEHOLDERS = [
    "bini.taddesse@vydia.com",
    #"commerce@vydia.com",
    #"jessica.bryant@vydia.com",
    #"jenna.gaudio@vydia.com",
    #"karalee.ensign@vydia.com",
    #"techservices@vydia.com"
]

def get_date_range():
    """
    Calculate the date range from last Friday 12:00 AM to this Friday 11:59 PM in the Shopify store's time zone.
    """
    store_timezone = pytz.timezone("America/New_York")
    now = datetime.now(store_timezone)
    days_since_friday = (now.weekday() + 3) % 7
    last_friday = now - timedelta(days=days_since_friday, hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
    current_friday = last_friday + timedelta(days=7)

    return {
        "created_at_min": last_friday.strftime("%Y-%m-%dT00:00:00%z"),
        "created_at_max": current_friday.strftime("%Y-%m-%dT23:59:59%z"),
        "start_date": last_friday.strftime("%Y-%m-%d"),
        "end_date": current_friday.strftime("%Y-%m-%d")
    }

def upload_to_s3(file_path, bucket_name, object_name):
    """Upload a file to an S3 bucket."""
    try:
        s3_client.upload_file(file_path, bucket_name, object_name)
        logging.info(f"File {file_path} uploaded to S3 bucket {bucket_name} as {object_name}")
    except Exception as e:
        logging.error(f"Failed to upload file to S3: {e}")
        raise

def generate_report():
    print("Starting data extraction and report generation...")

    # Fetch the date range
    date_range = get_date_range()
    print(f"Generating report for {date_range['start_date']} to {date_range['end_date']}")
    start_date = date_range["start_date"]
    end_date = date_range["end_date"]

    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    orders_url = (
        f"https://{SHOP_NAME}.myshopify.com/admin/api/2023-04/orders.json?"
        f"status=any&created_at_min={date_range['created_at_min']}&created_at_max={date_range['created_at_max']}&limit=250"
    )
    products_url = f"https://{SHOP_NAME}.myshopify.com/admin/api/2023-04/products.json?limit=250"

    # Fetch Orders
    all_orders = []
    current_url = orders_url
    while current_url:
        orders_response = requests.get(current_url, headers=headers)
        if orders_response.status_code == 200:
            data = orders_response.json()
            batch_orders = data.get('orders', [])
            all_orders.extend(batch_orders)
            print(f"Fetched {len(batch_orders)} orders in the current batch.")
            current_url = None
            if 'Link' in orders_response.headers:
                links = orders_response.headers['Link'].split(',')
                for link in links:
                    if 'rel="next"' in link:
                        current_url = link.split(';')[0].strip('<>')
        else:
            print(f"Error retrieving orders: {orders_response.status_code}")
            return None, start_date, end_date

    print(f"Total orders retrieved from Shopify API: {len(all_orders)}")

    # Filter valid (non-canceled and unique) orders
    unique_orders = {order['id']: order for order in all_orders if not order.get("cancelled_at")}
    valid_orders = list(unique_orders.values())
    print(f"Total valid (non-canceled and unique) orders: {len(valid_orders)}")

    # Fetch Products
    products_response = requests.get(products_url, headers=headers)
    if products_response.status_code == 200:
        products_data = products_response.json().get('products', [])
        product_lookup = {product['id']: product for product in products_data}
    else:
        print(f"Error retrieving products: {products_response.status_code}")
        product_lookup = {}

    # Handle the case where there are no valid orders
    if not valid_orders:
        print("No valid orders found in the specified date range.")
        report_df = pd.DataFrame([{
            "Order ID": "No Orders",
            "Order Date": "",
            "Customer Email": "",
            "Gross Sales": 0.0,
            "Shipping Cost": 0.0,
            "Total Sales": 0.0
        }])
    else:
        # Enrich Order Data
        enriched_orders = []
        for order in valid_orders:
            gross_sales = sum(float(item['price']) * float(item['quantity']) for item in order['line_items'])
            shipping_cost = float(order.get('total_shipping_price_set', {}).get('shop_money', {}).get('amount', 0))
            total_sales = gross_sales + shipping_cost

            enriched_order = {
                "Order ID": order['id'],
                "Order Date": order['created_at'],
                "Customer Email": order.get('email', 'N/A'),
                "Gross Sales": gross_sales,
                "Shipping Cost": shipping_cost,
                "Total Sales": total_sales
            }
            enriched_orders.append(enriched_order)

        # Create DataFrame
        report_df = pd.DataFrame(enriched_orders)

        # Calculate Totals
        total_gross_sales = report_df['Gross Sales'].sum()
        total_shipping = report_df['Shipping Cost'].sum()
        total_sales = report_df['Total Sales'].sum()

        print(f"Total Gross Sales (calculated): {total_gross_sales}")
        print(f"Total Shipping Cost (calculated): {total_shipping}")
        print(f"Total Sales (calculated): {total_sales}")

        # Add a totals row
        totals_row = {
            "Order ID": "Total",
            "Order Date": "",
            "Customer Email": "",
            "Gross Sales": total_gross_sales,
            "Shipping Cost": total_shipping,
            "Total Sales": total_sales
        }
        report_df = pd.concat([report_df, pd.DataFrame([totals_row])], ignore_index=True)

    # Save locally
    file_name = f"{SHOP_NAME.replace('-', ' ').title()} Weekly Report ({start_date} to {end_date}).csv"
    output_file_path = os.path.join(os.path.dirname(__file__), file_name)
    report_df.to_csv(output_file_path, index=False)
    print(f"Report saved at {output_file_path}")

    # Upload to S3
    bucket_name = os.getenv("S3_BUCKET_NAME")
    object_name = f"{SHOP_NAME}/weekly_reports/{file_name}"
    upload_to_s3(output_file_path, bucket_name, object_name)
    print(f"Uploaded to S3 with key: {object_name}")

    return output_file_path, start_date, end_date


def send_email_with_report():
    try:
        # Call the generate_report function and unpack its return values
        output_file_path, start_date, end_date = generate_report()  # Adjusted to unpack three values

        # Define bucket name and S3 object key
        bucket_name = os.getenv("S3_BUCKET_NAME")
        file_name = os.path.basename(output_file_path)
        object_name = f"shop-vydia/weekly_reports/{file_name}"

        # Debugging: Confirm paths
        print(f"Attempting to download from S3 bucket {bucket_name} with key {object_name}.")

        # Download the file from S3
        local_temp_file = os.path.join("/tmp", file_name)  # Save to a temporary local file
        s3_client.download_file(bucket_name, object_name, local_temp_file)
        print(f"File downloaded from S3 to {local_temp_file}")

        # Email details
        subject = f"Weekly Shopify Sales Report ({start_date} to {end_date})"
        body = f"Please find attached the Shopify sales report for the week of {start_date} to {end_date}."

        # Create email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = ", ".join(STAKEHOLDERS)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Attach the CSV file
        if os.path.exists(local_temp_file):
            with open(local_temp_file, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{file_name}"',
            )
            msg.attach(part)
        else:
            print(f"Error: File not found at {local_temp_file}")
            return

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, STAKEHOLDERS, msg.as_string())

        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Schedule the task to run at noon Eastern Time every Friday
eastern = pytz.timezone("US/Eastern")
#schedule.every().friday.at("9:00").do(send_email_with_report)
schedule.every(1).minute.do(send_email_with_report)


if __name__ == "__main__":
    print("Scheduler is running. Waiting for the next Friday at noon Eastern Time...")
    while True:
        schedule.run_pending()
        time.sleep(60)

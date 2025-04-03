Shopify Report Automation

Automatically generate and email weekly sales reports from a Shopify store, complete with product titles, shipping cost, and gross/total sales. Reports are uploaded to AWS S3 and sent to designated stakeholders.

Features
	•	📦 Fetches weekly order data from the Shopify API
	•	🧾 Generates detailed CSV reports with:
	•	Product Title
	•	Order ID
	•	Order Date
	•	Customer Email
	•	Gross Sales
	•	Shipping Cost
	•	Total Sales
	•	☁️ Uploads reports to AWS S3
	•	📧 Emails the reports to stakeholders every Friday at 9:00 AM EST

Technologies Used
	•	Python 3.9+
	•	Shopify Admin API
	•	Boto3 (AWS S3 Integration)
	•	schedule (Job scheduling)
	•	smtplib + email (Email automation)
	•	python-dotenv (Environment variable management)

Setup
	1.	Clone the Repo:

git clone https://github.com/bini1995/Shopify-Report-Automation.git
cd Shopify-Report-Automation


	2.	Create .env file (Don’t check this into Git!):

ACCESS_TOKEN=your_shopify_access_token
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
EMAIL_USER=your_email@example.com
EMAIL_PASSWORD=your_email_password
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_REGION=your_aws_region
S3_BUCKET_NAME=your_bucket_name


	3.	Install dependencies:

pip install -r requirements.txt


	4.	Run the Script:

python weekly_automation_script.py



The script will run in the background and send out a report every Friday at 9:00 AM EST.

Output Example

A sample row in the report CSV:

Product Title,Order ID,Order Date,Customer Email,Gross Sales,Shipping Cost,Total Sales
"Freedom T-Shirt",1234567890,2024-12-01T14:22:00Z,john@example.com,29.98,5.99,35.97

License

MIT

⸻

Made with ❤️ by Bini Taddesse

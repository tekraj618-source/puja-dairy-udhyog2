# Puja Dairy Udhyog — Professional Flask Website

A multi-page dairy business website with:
- Premium responsive frontend
- Product/rate page
- Online delivery/order form
- Order tracking by order ID + phone
- Contact/inquiry form
- Owner login
- Owner dashboard for orders, inquiries and product prices
- SQLite database
- Secure password hashing
- Render deployment files

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:
   pip install -r requirements.txt
4. Set an owner password before production:
   Windows PowerShell:
   $env:ADMIN_PASSWORD="YourStrongPasswordHere"
   $env:SECRET_KEY="a-long-random-secret"
5. Start:
   python app.py
6. Open http://127.0.0.1:5000

Owner panel:
http://127.0.0.1:5000/owner

Default username is `owner` unless ADMIN_USERNAME is changed.
Do not use the example password in production.

## Render

Create a new Web Service from this project.
Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app

Environment variables:
ADMIN_USERNAME = owner
ADMIN_PASSWORD = your strong password
SECRET_KEY = a long random secret

For production, move SQLite to PostgreSQL if you expect many orders or multiple servers.

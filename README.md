# QuickConnect

QuickConnect is a platform designed to connect clients with professionals instantly. Built using **Django** for the backend and **React Native** for the mobile application, the system provides seamless communication, scheduling, and service management between users and service providers.

## Features

- **User Authentication**: Secure login and registration for both clients and professionals.
- **Instant Matching**: AI-based algorithm connects clients to the first available professional in the selected category.
- **Session Management**: Clients can request and track active service sessions.
- **Payment Integration**: M-Pesa STK push support for easy payments.
- **Admin Panel**: Manage users, professionals, and service analytics efficiently.

## Tech Stack

- **Backend**: Django, Django REST Framework
- **Frontend**: React Native, Expo
- **Database**: PostgreSQL (or SQLite for development)
- **Payment Gateway**: M-Pesa Daraja API
- **Deployment**: AWS

## Installation

1. Clone the repository: git clone https://github.com/eKidenge/QuickConnect.git
2. Navigate to the project directory: cd QuickConnect
3. Set up the Python environment: python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
4. Run migrations: python manage.py migrate
5. Start the development server:
   cd mobile
   npm install
   expo start

7. For the mobile app:
Usage

Clients can browse categories and request instant matching with professionals.

Professionals can accept or decline sessions and track their assignments.

Admins can monitor all user activity and manage system data.

Contributing

Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request.

License

This project is licensed under the MIT License. See the LICENSE
 file for details.

QuickConnect — Making professional services instantly accessible


```bash
git clone https://github.com/eKidenge/QuickConnect.git

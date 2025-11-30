# Library Management System

A simple, lightweight library management system built with Flask that allows users to search, borrow, and return books. This project demonstrates various software design patterns including State, Observer, Strategy, Singleton, and Iterator patterns.

## 🛠️ Tech Stack

- **Backend**: Flask 3.0.0
- **Real-time Communication**: Flask-SocketIO 5.3.6
- **Security**: Werkzeug (password hashing)
- **Frontend**: HTML5, CSS3, JavaScript
- **Data Storage**: Pickle (file-based persistence)

## 📋 Features

- **User Authentication**: Register and login system with secure password hashing
- **Book Search**: Search for books by title (case-insensitive)
- **Book Borrowing**: Borrow available books with payment processing
- **Book Returns**: Return borrowed books
- **Real-time Updates**: Live book availability updates using WebSockets (Socket.IO)
- **Payment Integration**: Support for multiple payment methods (Card, UPI)
- **User Dashboard**: View all borrowed books in one place

## 🚀 How to Run

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd library-management-system
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - The application will run in debug mode

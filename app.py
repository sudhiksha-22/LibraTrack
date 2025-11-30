"""
Library Management System - Flask Application

A simple library management system that allows users to:
- Register and login
- Search for books
- Borrow and return books
- Make payments for book rentals

Uses design patterns: State, Observer, Strategy, Singleton, Iterator
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from abc import ABC, abstractmethod
import os
import pickle


# ============================================================================
# Flask Application Setup
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")


# ============================================================================
# Design Pattern: State Pattern - Book Availability States
# ============================================================================

class BookState:
    """Base class for book availability states."""
    
    def borrow_book(self, book, user):
        """Attempt to borrow a book."""
        pass

    def return_book(self, book):
        """Return a book."""
        pass


class AvailableState(BookState):
    """State representing an available book."""
    
    def display_status(self):
        """Return the status string."""
        return "Available"

    def borrow_book(self, book, user):
        """Borrow an available book."""
        book.state = UnavailableState()
        book.borrower = user
        book.notify_observers(book)
        return True
    
    def return_book(self, book):
        """No action needed for available books."""
        pass


class UnavailableState(BookState):
    """State representing an unavailable/borrowed book."""
    
    def display_status(self):
        """Return the status string."""
        return "Unavailable"

    def borrow_book(self, book, user):
        """Cannot borrow an unavailable book."""
        return False

    def return_book(self, book):
        """Return a book and make it available again."""
        book.state = AvailableState()
        borrower = book.borrower
        book.borrower = None
        if borrower:
            borrower.return_book(book)
        book.notify_observers(book)


# ============================================================================
# Design Pattern: Observer Pattern - Book Updates
# ============================================================================

class Observer:
    """Base observer class for book updates."""
    
    def update(self, book):
        """Receive update notification about a book."""
        pass


class UserObserver(Observer):
    """Observer that notifies users about book updates."""
    
    def __init__(self, user):
        self.user = user

    def update(self, book):
        """Notify user when a book they're interested in is borrowed."""
        print(f"Dear {self.user.user_id}, the book '{book.title}' has been borrowed.")


class Observable:
    """Base class for objects that can be observed."""
    
    def __init__(self):
        self.observers = []

    def add_observer(self, observer):
        """Add an observer to the list."""
        self.observers.append(observer)

    def remove_observer(self, observer):
        """Remove an observer from the list."""
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self, book):
        """Notify all observers about a book update."""
        for observer in self.observers:
            observer.update(book)


class WebPageObserver(Observer):
    """Observer that sends real-time updates to web clients via SocketIO."""
    
    def __init__(self, socketio):
        self.socketio = socketio

    def update(self, book):
        """Emit book update to connected web clients."""
        self.socketio.emit('book_update', {
            'book_id': book.id,
            'availability': book.display_status()
        }, namespace='/update')


# ============================================================================
# Book Model
# ============================================================================

class Book(Observable):
    """Represents a book in the library."""
    
    def __init__(self, book_id, title, author, description, availability, image_url, price):
        super().__init__()
        self.id = book_id
        self.title = title
        self.author = author
        self.description = description
        self.price = price
        self.state = AvailableState()
        self.image_url = image_url
        self.borrower = None
        # Add web observer for real-time updates
        self.add_observer(WebPageObserver(socketio))

    def display_status(self):
        """Get the current availability status."""
        return self.state.display_status()

    def borrow_book(self, user, payment_strategy=None):
        """Borrow this book for a user."""
        if self.display_status() == "Available":
            self.state = UnavailableState()
            self.borrower = user
            self.notify_observers(self)
            user.borrow_book(self, payment_strategy=payment_strategy)
            return True
        return False

    def return_book(self):
        """Return this book to the library."""
        if self.borrower:
            self.state = AvailableState()
            borrower = self.borrower
            self.borrower = None
            borrower.return_book(self)
            self.notify_observers(self)


# ============================================================================
# Design Pattern: Strategy Pattern - Payment Methods
# ============================================================================

class PaymentStrategy(ABC):
    """Abstract base class for payment strategies."""
    
    @abstractmethod
    def make_payment(self, user, book):
        """Process payment for a book rental."""
        pass


class CardPaymentStrategy(PaymentStrategy):
    """Payment strategy for credit/debit card payments."""
    
    def make_payment(self, user, book):
        """Process card payment (simplified - always succeeds)."""
        return True


class UPIPaymentStrategy(PaymentStrategy):
    """Payment strategy for UPI payments."""
    
    def make_payment(self, user, book):
        """Process UPI payment (simplified - always succeeds)."""
        return True


class PaymentContext:
    """Context class for executing payment strategies."""
    
    def __init__(self, strategy):
        self._strategy = strategy

    def execute_payment(self, user, book):
        """Execute the payment using the selected strategy."""
        return self._strategy.make_payment(user, book)


# ============================================================================
# User Model
# ============================================================================

class User:
    """Represents a library user."""
    
    def __init__(self, user_id, password, payment_strategy=None):
        self.user_id = user_id
        self.password_hash = generate_password_hash(password)
        self.borrowed_books = set()
        self.observers = []
        self.payment_strategy = payment_strategy

    def verify_password(self, password):
        """Verify if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def borrow_book(self, book, payment_strategy=None):
        """Borrow a book and add it to user's borrowed list."""
        self.borrowed_books.add(book.id)
        book.add_observer(UserObserver(self))
        book.borrow_book(self, payment_strategy=payment_strategy)

    def get_borrowed_books(self):
        """Get list of books currently borrowed by this user."""
        return [book for book in books_instance if book.id in self.borrowed_books]

    def return_book(self, book):
        """Return a borrowed book."""
        if book.id in self.borrowed_books:
            self.borrowed_books.remove(book.id)
            book.return_book()


# ============================================================================
# Design Pattern: Iterator Pattern - Book Iteration
# ============================================================================

class BookIterator:
    """Iterator for iterating through books."""
    
    def __init__(self, books):
        self.books = books
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self.books):
            result = self.books[self.index]
            self.index += 1
            return result
        raise StopIteration


# ============================================================================
# Design Pattern: Singleton Pattern - Book List
# ============================================================================

class BookList:
    """Singleton class managing the collection of books."""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance exists."""
        if not cls._instance:
            cls._instance = super(BookList, cls).__new__(cls)
        return cls._instance

    def __init__(self, books):
        """Initialize the book list (only once)."""
        if not hasattr(self, 'initialized'):
            self.books = books
            self.initialized = True

    def search_by_title(self, title):
        """Search for books by title (case-insensitive)."""
        if not title:
            return []
        return [book for book in self.books if title.lower() in book.title.lower()]

    def __iter__(self):
        """Return an iterator for the books."""
        return BookIterator(self.books)


# ============================================================================
# Data Persistence
# ============================================================================

def load_user_data():
    """Load user data from pickle file."""
    try:
        with open('users.pickle', 'rb') as file:
            return pickle.load(file)
    except FileNotFoundError:
        return {}


def save_user_data(users):
    """Save user data to pickle file."""
    with open('users.pickle', 'wb') as file:
        pickle.dump(users, file)


# ============================================================================
# Initialize Application Data
# ============================================================================

# Initialize book collection
books_instance = BookList([
    Book(1, 'Dive into Design Patterns', 'Alexander Shvets',
         'A timeless guide to common software design challenges, offering elegant solutions through proven design patterns.',
         'Available', 'https://refactoring.guru/images/patterns/book/web-cover-en.png', 60),
    Book(2, 'Design Patterns - Elements of OOPS', 'Erich Gamma',
         'Comprehensive exploration of design patterns, focusing on practical applications and real-world examples.',
         'Available', 'https://m.media-amazon.com/images/I/51nL96Abi1L.jpg', 55),
    Book(3, 'Heads First Design Patterns', 'Eric Freeman',
         'Fun introduction to essential design patterns for software development.',
         'Available', 'https://miro.medium.com/v2/resize:fit:864/0*Dmzt5gDgHxXqtcf-.jpg', 70),
    Book(4, 'Learning Python Design Patterns', 'Chetan Giridhar',
         'Providing valuable insights into designing scalable and maintainable software systems.',
         'Available', 'https://m.media-amazon.com/images/W/MEDIAX_792452-T2/images/I/81qk22hoUqL._AC_UF1000,1000_QL80_.jpg', 80),
    Book(5, 'Design Patterns with Python', 'Harry J W Percival',
         'Application of design patterns for creating maintainable and readable software.',
         'Available', 'https://cdn.kobo.com/book-images/bb7fa2c5-64bc-46cc-aaf6-4e3e11b7b03d/353/569/90/False/architecture-patterns-with-python.jpg', 65),
])

# Global user state (in production, use session-based user management)
current_user = None
users = load_user_data()


# ============================================================================
# Helper Functions
# ============================================================================

def get_book_by_id(book_id):
    """Find a book by its ID."""
    for book in books_instance:
        if book.id == book_id:
            return book
    return None


def require_login():
    """Check if user is logged in, redirect to login if not."""
    global current_user
    if not current_user:
        return redirect(url_for('user_login'))
    return None


# ============================================================================
# Flask Routes
# ============================================================================

@app.route('/')
def index():
    """Home page - welcome screen."""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate input
        if not user_id:
            return render_template('register.html', 
                                 message='Username cannot be empty.', 
                                 success=False)
        if not password:
            return render_template('register.html', 
                                 message='Password cannot be empty.', 
                                 success=False)
        
        # Check if user already exists
        if user_id in users:
            return render_template('register.html', 
                                 message='User already exists. Choose a different username.', 
                                 success=False)
        
        # Create new user and save
        new_user = User(user_id, password)
        users[user_id] = {
            'password_hash': new_user.password_hash
        }
        save_user_data(users)
        
        return render_template('register.html', 
                             message='Registered successfully. You can now log in.', 
                             success=True)
    
    return render_template('register.html', message=None, success=False)


@app.route('/user-login', methods=['GET', 'POST'])
def user_login():
    """User login page."""
    global current_user
    
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate input
        if not user_id or not password:
            return render_template('user-login.html', 
                                 message='Please enter both username and password.')
        
        # Check if user exists
        if user_id not in users:
            return render_template('user-login.html', 
                                 message='User not found. Please check your username.')
        
        # Verify password
        stored_user = users[user_id]
        # Handle both old format (plain text) and new format (hash)
        if 'password_hash' in stored_user:
            user = User(user_id, 'temp')  # Temporary password
            user.password_hash = stored_user['password_hash']
            if not user.verify_password(password):
                return render_template('user-login.html', 
                                     message='Incorrect password. Please try again.')
        else:
            # Legacy support for old plain text passwords
            if stored_user.get('password') != password:
                return render_template('user-login.html', 
                                     message='Incorrect password. Please try again.')
            # Migrate to hashed password
            user = User(user_id, password)
            users[user_id] = {'password_hash': user.password_hash}
            save_user_data(users)
        
        # Login successful - create user instance
        current_user = User(user_id, password)
        # Restore borrowed books if they exist in stored data
        if 'borrowed_books' in stored_user:
            current_user.borrowed_books = set(stored_user['borrowed_books'])
        session['user_id'] = user_id
        
        return redirect(url_for('search'))
    
    return render_template('user-login.html', message=None)


@app.route('/logout')
def logout():
    """Logout user and redirect to home."""
    global current_user
    current_user = None
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    """Book search page."""
    global current_user
    
    # Check if user is logged in
    login_check = require_login()
    if login_check:
        return login_check
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        results = books_instance.search_by_title(search_query) if search_query else []
        return render_template('search.html', 
                             results=results, 
                             user=current_user, 
                             book=None, 
                             csrf_token=session.get('csrf_token'))
    
    return render_template('search.html', 
                         results=None, 
                         user=current_user, 
                         book=None, 
                         csrf_token=session.get('csrf_token'))


@app.route('/borrow/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    """API endpoint to borrow a book."""
    global current_user
    
    if not current_user:
        return jsonify({'message': 'Please log in to borrow books.', 'availability': 'Available'}), 401
    
    book = get_book_by_id(book_id)
    if not book:
        return jsonify({'message': 'Book not found.', 'availability': 'Available'}), 404
    
    if book.display_status() == "Available":
        success = current_user.borrow_book(book)
        if success:
            socketio.emit('book_update', {
                'book_id': book.id,
                'availability': 'Unavailable'
            }, namespace='/update')
            return jsonify({
                'message': 'Book borrowed successfully!',
                'availability': 'Unavailable'
            })
    
    return jsonify({
        'message': 'Failed to borrow the book. The book is not available.',
        'availability': book.display_status()
    }), 400


@app.route('/return/<int:book_id>', methods=['POST'])
def return_book(book_id):
    """API endpoint to return a book."""
    global current_user
    
    if not current_user:
        return jsonify({'message': 'Please log in to return books.'}), 401
    
    book = get_book_by_id(book_id)
    if not book:
        return jsonify({'message': 'Book not found.'}), 404
    
    if book.id not in current_user.borrowed_books:
        return jsonify({'message': 'You have not borrowed this book.'}), 400
    
    try:
        current_user.return_book(book)
        socketio.emit('book_update', {
            'book_id': book.id,
            'availability': 'Available'
        }, namespace='/update')
        socketio.emit('notification', {
            'message': 'Book returned successfully!',
            'type': 'success'
        }, namespace='/update')
        return jsonify({
            'message': 'Book returned successfully!',
            'availability': 'Available'
        })
    except Exception as e:
        app.logger.error(f"Error returning book: {str(e)}")
        return jsonify({'message': 'Failed to return the book. Please try again.'}), 500


@app.route('/user-page')
def user_page():
    """User dashboard showing borrowed books."""
    global current_user
    
    # Check if user is logged in
    login_check = require_login()
    if login_check:
        return login_check
    
    borrowed_books = current_user.get_borrowed_books() if current_user else []
    return render_template('user-page.html', 
                         user=current_user, 
                         borrowed_books=borrowed_books)


@app.route('/payment/<int:book_id>', methods=['GET'])
def payment(book_id):
    """Payment page for borrowing a book."""
    global current_user
    
    # Check if user is logged in
    login_check = require_login()
    if login_check:
        return login_check
    
    book = get_book_by_id(book_id)
    if not book or book.display_status() != "Available":
        return redirect(url_for('search'))
    
    return render_template('payment.html', book=book, price=book.price)


@app.route('/make-payment/<int:book_id>', methods=['POST'])
def make_payment(book_id):
    """API endpoint to process payment and borrow a book."""
    global current_user
    
    if not current_user:
        return jsonify({'message': 'Please log in to make a payment.', 'success': False}), 401
    
    book = get_book_by_id(book_id)
    if not book or book.display_status() != "Available":
        return jsonify({
            'message': 'Book is not available for borrowing.',
            'success': False
        }), 400
    
    payment_method = request.form.get('payment_method')
    if payment_method == 'card':
        payment_strategy = CardPaymentStrategy()
    elif payment_method == 'upi':
        payment_strategy = UPIPaymentStrategy()
    else:
        return jsonify({
            'message': 'Unsupported payment method.',
            'success': False
        }), 400
    
    success = current_user.borrow_book(book, payment_strategy=payment_strategy)
    if success:
        socketio.emit('book_update', {
            'book_id': book.id,
            'availability': 'Unavailable'
        }, namespace='/update')
        return jsonify({
            'message': 'Payment successful! Book borrowed successfully.',
            'success': True,
            'redirect': url_for('user_page')
        })
    
    return jsonify({
        'message': 'Failed to borrow the book after payment.',
        'success': False
    }), 500


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    socketio.run(app, debug=True)

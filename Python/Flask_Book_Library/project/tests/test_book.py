import pytest
from project import app, db
from project.books.models import (Book)


@pytest.fixture(scope='module')
def test_app():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def session(test_app):
    with test_app.app_context():
        yield db.session
        db.session.rollback()

@pytest.mark.parametrize("name, author, year, book_type", [
    ("It", "Stephen King", 1986, "Horror"),
    ("Dune", "Frank Herbert", 1965, "Science Fiction"),
    ("The Witcher", "Andrzej Sapkowski", 1993, "Fantasy"),
    ("The Lord of the Rings", "J.R.R. Tolkien", 1954, "Fantasy"),
    ("Brave New World", "Aldous Huxley", 1932, "Dystopian")
])
def test_valid_book_data(session, name, author, year, book_type):
    book = Book(name=name, author=author, year_published=year, book_type=book_type)
    session.add(book)
    session.commit()

    fetched_book = Book.query.filter_by(name=name).first()
    assert fetched_book is not None
    assert fetched_book.name == name
    assert fetched_book.author == author
    assert fetched_book.year_published == year
    assert fetched_book.book_type == book_type
    assert fetched_book.status == "available"


@pytest.mark.parametrize("invalid_data", [
    {"name": "", "author": "Author", "year_published": 2021, "book_type": "Horror"},  # Empty name
    {"name": "Valid Name", "author": None, "year_published": 2021, "book_type": "Fiction"},  # Empty author
    {"name": "Valid Name", "author": "Author", "year_published": -1, "book_type": "Fantasy"},  # Invalid year
    {"name": "Valid Name", "author": "Author", "year_published": 2021, "book_type": ""}  # Empty book type
])
def test_invalid_book_data(session, invalid_data):
    with pytest.raises(Exception):
        book = Book(**invalid_data)
        session.add(book)
        session.commit()


@pytest.mark.parametrize("sqli_payload", [
    "1' OR '1'='1",
    "' OR '1'='1' --",
    "1; DROP TABLE books; --",
    "'; SELECT * FROM users WHERE '1'='1",
    "1' UNION SELECT null, null, null, null, null; --",
    "' OR 'a'='a",
])
@pytest.mark.parametrize("field", ["name", "author", "year_published", "book_type"])
def test_sql_injection(session, sqli_payload, field):
    valid_book_data = {"name": "Test Book", "author": "Test Author", "year_published": 2024, "book_type": "Fantasy",
                       field: sqli_payload}

    book = Book(**valid_book_data)

    with pytest.raises(Exception):
        session.add(book)
        session.commit()


@pytest.mark.parametrize("xss_payload", [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "'-prompt(8)-'",
    "<body onload=alert('XSS')>",
    "<iframe src='javascript:alert(`XSS`)'></iframe>",
    "javascript:alert('XSS')",
])
@pytest.mark.parametrize("field", ["name", "author", "year_published", "book_type"])
def test_xss_injection(session, xss_payload, field):
    valid_book_data = {"name": "Test Book", "author": "Test Author", "year_published": 2024, "book_type": "Fantasy",
                       field: xss_payload}

    book = Book(**valid_book_data)

    with pytest.raises(Exception):
        session.add(book)
        session.commit()


@pytest.mark.parametrize("lengths", [1000, 10000, 100000])
def test_extreme_cases(session, lengths):
    very_long_name = "X" * lengths
    very_long_author = "Y" * lengths
    with pytest.raises(Exception):
        book = Book(name=very_long_name, author=very_long_author, year_published=2024, book_type="Fantasy")
        db.session.add(book)
        db.session.commit()

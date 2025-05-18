from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import secrets
import os
from werkzeug.security import generate_password_hash, check_password_hash
import chardet
import ebooklib
from ebooklib import epub
import fitz
import mobi
from docx import Document
#   from BooksApp import app, db
#   app.app_context().push()
#   db.create_all()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///BooksAppDB.db'
app.secret_key = secrets.token_hex(16)  # Генерирует случайный 32-символьный шестнадцатеричный ключ
print("Случаный secret_key: "+app.secret_key)
db = SQLAlchemy(app)


#База данных пользователей
class Authorization(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    Name = db.Column(db.String(100), nullable = False)
    Password = db.Column(db.String(100), nullable = False)
    Rank = db.Column(db.String(100), nullable = False)
#База данных книг
class Books(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    Title = db.Column(db.String(100), nullable = False)
    Cover = db.Column(db.String(100), nullable = False)
    Author = db.Column(db.String(100), nullable = False)
    About = db.Column(db.Text, nullable = False)
    File_path = db.Column(db.String(100), nullable = False)
#База данных закладок пользователей
class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    user_id = db.Column(db.Integer, db.ForeignKey('authorization.id'), nullable=False)  
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)  

    user = db.relationship('Authorization', backref='bookmarks')  
    book = db.relationship('Books', backref='bookmarks') 


#Регистрация пользователей
@app.route("/Registration", methods=['POST', 'GET'])
def Registration():
    if request.method == 'POST':
        username = request.form['Login']
        pswrd_check = request.form['Password']
       
        if Authorization.query.filter_by(Name=username).first():
            flash('Данный логин уже существует!')
            return redirect(url_for('Registration')) 
        if len(username) < 4:
            flash('Логин должен содержать не менее 4 символов.')
            return redirect(url_for('Registration'))
        if len(pswrd_check) < 6:
            flash('Пароль должен содержать не менее 6 символов.')
            return redirect(url_for('Registration'))
        
        pswrd = generate_password_hash(request.form['Password'])
        rank = "User"
        reg = Authorization(Name = username, Password = pswrd, Rank = rank)
        try:
            db.session.add(reg)
            db.session.commit()

            session['username'] = username
            return redirect('/')
        except:
                return 'При регистрации что-то пошло не так'
    else:        
        return render_template('Registration.html')
#Вход в аккаунт
@app.route("/Log_in", methods=['POST', 'GET'])
def Log_in():
    if request.method == 'POST':
        username = request.form['Login']
        pswrd = request.form['Password']
        
        # Поиск пользователя в базе данных
        user = Authorization.query.filter_by(Name=username).first()
        
        if user and check_password_hash(user.Password, pswrd):
            session['username'] = username
            return redirect('/')  # Главная страница
        else:
            flash('Неверное имя пользователя или пароль!')
            return render_template('Log_in.html')
    return render_template('Log_in.html')
#logout       
@app.route('/logout')
def logout():
    session.pop('username', None)  # Удаление имени пользователя из сессии
    return redirect('/')


#Главная
@app.route("/Main")
@app.route("/")
def Main():
    username = session.get('username') 
    books = Books.query.all()
    admin=False
    if 'username' not in session:
        return render_template('Main.html', books=books)
    else:
        user = Authorization.query.filter_by(Name=username).first()
        if user.Rank == 'Admin':
            admin=True
        return render_template('Main.html', books=books, username=username, admin=admin)


#Просмотр книги
@app.route('/book/<int:id>')
def book_detail(id):
    book = Books.query.get_or_404(id)
    cover_path = book.Cover
    cover_url= url_for('static', filename=cover_path)
    username = session.get('username')
    if 'username' not in session:
        return render_template('Book.html', book=book, cover_url = cover_url)
    else:
        user = Authorization.query.filter_by(Name=username).first()
        admin=False
        if user.Rank == 'Admin':
            admin=True
        return render_template('Book.html', book=book, cover_url = cover_url, username=username, admin=admin)

#Добавление книг в базу данных  
@app.route("/AddBooks", methods=['POST', 'GET'])
def AddBooks():
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему, чтобы добавлять книги.')
        return redirect('/Log_in')
    username = session.get('username')
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        about = request.form['about']
        file_path = "book/"+request.form['file_path']
        cover = "Cover/"+request.form['cover']

        Add = Books(Title = title, Cover = cover, Author = author, About = about, File_path = file_path)
        if Books.query.filter_by(Title=title).first():
            return "Данная книга уже существует!"
        try:
            db.session.add(Add)
            db.session.commit()
            return redirect('/')
        except:
            return 'При добавлении книги что-то пошло не так'
    else:        
        return render_template('AddBooks.html', username=username)

#Удаление книг
@app.route("/book/<int:id>/del")
def delete_book(id):
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему.')
        return redirect('/Log_in')

    del_book = Books.query.get_or_404(id)
    try:
        db.session.delete(del_book)
        db.session.commit()
        return redirect('/')
    except:
        return 'При удалении книги что-то пошло не так'    

#Изменение книг
@app.route("/book/<int:id>/edit", methods=['POST', 'GET'])
def BookUpdate(id):
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему, чтобы добавлять книги.')
        return redirect('/Log_in')
    username = session.get('username')
    edit = Books.query.get_or_404(id)
    if request.method == 'POST':
        edit.Title = request.form['title']
        edit.Author = request.form['author']
        edit.About = request.form['about']
        edit.File_path = request.form['file_path']
        edit.Cover = request.form['cover']

        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'При изменении что-то пошло не так'
    else:   
        
        return render_template('Book_edit.html', edited=edit, username=username)

#Закладки
@app.route('/Bookmarks')
def Bookmarks():
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему, чтобы просмотреть закладки.')
        return redirect('/Log_in')
    username = session.get('username')
    user = Authorization.query.filter_by(Name=session['username']).first()
    bookmarks = Bookmark.query.filter_by(user_id=user.id).all()
    return render_template('Bookmarks.html', bookmarks=bookmarks,  username=username)

#Добавление закладок
@app.route('/add_bookmark/<int:book_id>', methods=['POST'])
def add_bookmark(book_id):
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему, чтобы добавлять закладки.')
        return redirect('/Log_in')
    
    user = Authorization.query.filter_by(Name=session['username']).first()

    #Проверка, существует ли уже закладка
    existing_bookmark = Bookmark.query.filter_by(user_id=user.id, book_id=book_id).first()

    #Удаление закладки если она уже существовала
    if existing_bookmark:
        flash('Книга убрана из закладок!')
        return remove_bookmark(existing_bookmark.id)
    
    # Если закладки нет, добавляем новую
    bookmark = Bookmark(user_id=user.id, book_id=book_id)
    db.session.add(bookmark)
    db.session.commit()

   
    
    str_id = str(book_id)
    flash('Книга добавлена в закладки!')
    return redirect('/book_log/'+str_id, )

#Удаление закладок
@app.route('/remove_bookmark/<int:bookmark_id>', methods=['POST'])
def remove_bookmark(bookmark_id):
    bookmark = Bookmark.query.get(bookmark_id)
    str_id = str(bookmark.book_id)
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
    
    return redirect('/book_log/'+str_id)

#Проверка на добавленную закладку
@app.route('/check_bookmark/<int:book_id>', methods=['GET'])
def check_bookmark(book_id):
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему, чтобы добавлять закладки.')
        return redirect('/Log_in')
    
    user = Authorization.query.filter_by(Name=session['username']).first()

    #Проверка, существует ли уже закладка
    has_bookmark = Bookmark.query.filter_by(user_id=user.id, book_id=book_id).first() is not None

    #Если она уже существовала
    if has_bookmark:
         return {"has_bookmark" : True}
    return {"has_bookmark" : False}


#Поиск книг по названию
@app.route('/search_books', methods=['GET'])
def search_books():
    title = request.args.get('title', '')
    books = []
    username = session.get('username')
    user = Authorization.query.filter_by(Name=username).first()
    if title:
        books = Books.query.filter(Books.Title.ilike(f'%{title}%')).all()  # Поиск с нечувствительностью к регистру
    if 'username' not in session:
        return render_template('Main.html', books=books) # Возвращаем шаблон если зарегистрирован
        # Проверка ранга пользователя
    if user.Rank == 'Admin':
        return render_template('Main_adm.html', books=books, username=username)  # Перенаправление для админа
    else:
        return render_template('Main_log.html', books=books, username=username)  # Перенаправление для обычного пользователя


#Чтение книг
@app.route('/read_book/<int:book_id>')
def read_book(book_id):
    book = Books.query.get_or_404(book_id)
    file_path = book.File_path
    file_url= url_for('static', filename=file_path)

    return render_template('read_book.html', book=book, file_url = file_url)

#Создание пользователя с уровнем доступа админ если его еще нет(admin!secure!pswrd)
def create_admin_user():
    admin_user = Authorization.query.filter_by(Name='admin').first()
    
    if not admin_user:
        new_admin = Authorization(
            Name='admin',
            Password=generate_password_hash('admin!secure!pswrd'),  # Замените на ваш пароль
            Rank='Admin'
        )
        db.session.add(new_admin)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаем все таблицы, если их еще нет
        create_admin_user()  # Создаем пользователя с уровнем доступа админ, если его нет(admin!secure!pswrd)
    app.run(debug=True)

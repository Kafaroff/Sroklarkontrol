from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug.utils import secure_filename
from datetime import datetime
import pdfkit
import os
import base64
from PIL import Image
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///SrokKontrol.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
app.secret_key = 'supersecretkey'

# E-posta ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kamalqafarov.2006@gmail.com'
app.config['MAIL_PASSWORD'] = 'kamal.2006'

db = SQLAlchemy(app)
mail = Mail(app)

# PDF için wkhtmltopdf yolunu belirtin
pdfkit_config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')


# Model tanımı
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    photo_link = db.Column(db.String(200))
    section = db.Column(db.String(50), nullable=False)

# Kalan günleri hesaplama fonksiyonu
def calculate_days_left(expiration_date):
    today = datetime.now().date()
    days_left = (expiration_date - today).days
    return days_left

# Veritabanı tablolarını oluşturma
def create_tables():
    with app.app_context():
        db.create_all()

# Ana sayfa
@app.route('/')
def index():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))
    return render_template('index.html')

# Fotoğraf dosyasını kaydetme
def save_photo(photo):
    upload_folder = app.config['UPLOADED_PHOTOS_DEST']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    filename = secure_filename(photo.filename)
    photo_path = os.path.join(upload_folder, filename)
    photo.save(photo_path)
    return filename

# Fotoğrafı base64 formatında dönüştürme
def image_to_base64(image_path):
    with open(image_path, 'rb') as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Login sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        section = session.get('section')
        correct_passwords = {
            'SU SOBESİ': 'susobesi2024',
            'SİRNİYYAT SOBESİ': 'sirniyyatsobesi2024',
            'QURU QİDA SOBESİ': 'quruqidasobesi2024',
            'QASTRANOM SOBESİ': 'qastranomsobesi2024',
            'BÜTÜN SOBELER': 'butunsobeler2024'
        }
        if password == correct_passwords.get(section):
            session['authenticated'] = True
            return redirect(session.get('next', '/'))
        else:
            flash('Incorrect password. Please try again.')
    return render_template('login.html')

# Bölüm seçim sayfası
@app.route('/select_section', methods=['GET', 'POST'])
def select_section():
    if request.method == 'POST':
        section = request.form['section']
        password = request.form['password']
        correct_passwords = {
            'SU SOBESİ': 'susobesi2024',
            'SİRNİYYAT SOBESİ': 'sirniyyatsobesi2024',
            'QURU QİDA SOBESİ': 'quruqidasobesi2024',
            'QASTRANOM SOBESİ': 'qastranomsobesi2024',
            'BÜTÜN SOBELER': 'butunsobeler2024'
        }
        if password == correct_passwords.get(section):
            session['section'] = section
            session['authenticated'] = False
            return redirect(url_for('login'))
        else:
            flash('Incorrect password for selected section. Please try again.')
    return render_template('select_section.html')

# Ürün ekleme
@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))

    section = session.get('section')
    if request.method == 'POST':
        name = request.form['name']
        expiration_date = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d').date()

        if 'photo' in request.files:
            photo = request.files['photo']
            filename = save_photo(photo)
            photo_link = url_for('uploaded_file', filename=filename)
        else:
            photo_link = ''

        new_product = Product(name=name, expiration_date=expiration_date, photo_link=photo_link, section=section)
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!')
        return redirect(url_for('add_product'))
    return render_template('add.html')

# Fotoğraf görüntüleme
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)

# Tüm ürünleri listeleme
@app.route('/products')
def list_products():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))

    section = session.get('section')
    query = request.args.get('query')

    if section == 'BÜTÜN SOBELER':
        if query:
            products = Product.query.filter(Product.name.like(f"%{query}%")).order_by(Product.expiration_date.asc()).all()
        else:
            products = Product.query.order_by(Product.expiration_date.asc()).all()
    else:
        if query:
            products = Product.query.filter(Product.name.like(f"%{query}%"), Product.section == section).order_by(Product.expiration_date.asc()).all()
        else:
            products = Product.query.filter_by(section=section).order_by(Product.expiration_date.asc()).all()

    for product in products:
        product.days_left = calculate_days_left(product.expiration_date)
    return render_template('list.html', products=products, datetime=datetime)

# Belirli tarihler arasında son kullanma tarihi olan ürünleri listeleme
@app.route('/expired', methods=['GET', 'POST'])
def expired_products():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))

    section = session.get('section')
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        products = Product.query.filter(Product.expiration_date.between(start_date, end_date), Product.section == section).all()
        for product in products:
            product.days_left = calculate_days_left(product.expiration_date)
        return render_template('expired.html', products=products)
    return render_template('expired.html', products=[])

# Ürünü silme
@app.route('/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))

    section = session.get('section')
    product = Product.query.filter_by(id=id, section=section).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!')
    return redirect(url_for('list_products'))

# Belirli tarihler arasında olan ürünleri silme
@app.route('/delete_by_date', methods=['GET', 'POST'])
def delete_by_date():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))

    section = session.get('section')
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        products = Product.query.filter(Product.expiration_date.between(start_date, end_date), Product.section == section).all()
        for product in products:
            db.session.delete(product)
        db.session.commit()
        flash('Products deleted successfully!')
        return redirect(url_for('delete_by_date'))
    return render_template('delete_by_date.html')

# Rapor talep etme sayfası
@app.route('/report')
def report():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))
    return render_template('report.html')

# Rapor talep etme işlevi
@app.route('/request_report', methods=['POST'])
def request_report():
    if not session.get('authenticated'):
        return redirect(url_for('select_section'))

    section = session.get('section')
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()

    products = Product.query.filter(Product.expiration_date.between(start_date, end_date), Product.section == section).all()

    for product in products:
        if product.photo_link:
            filename = product.photo_link.split('/')[-1]
            photo_path = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename)
            product.photo_link_base64 = image_to_base64(photo_path)
        else:
            product.photo_link_base64 = None
        # Calculate days left and include in products
        product.days_left = calculate_days_left(product.expiration_date)

    pdf_content = render_template('report_template.html', products=products, start_date=start_date, end_date=end_date)

    pdf_output = pdfkit.from_string(pdf_content, False, configuration=pdfkit_config)

    response = make_response(pdf_output)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=expiration_report.pdf'
    return response
# Ana sayfa
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('select_section'))

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
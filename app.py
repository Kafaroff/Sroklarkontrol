from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///SrokKontrol.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'  # Fotoğrafların yükleneceği klasör
app.secret_key = 'supersecretkey'
db = SQLAlchemy(app)

# Model tanımı
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    photo_link = db.Column(db.String(200))


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


# Ürün ekleme
@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        expiration_date = datetime.strptime(request.form['expiration_date'], '%Y-%m-%d').date()

        if 'photo' in request.files:
            photo = request.files['photo']
            filename = save_photo(photo)
            photo_link = url_for('uploaded_file', filename=filename)
        else:
            photo_link = ''

        new_product = Product(name=name, expiration_date=expiration_date, photo_link=photo_link)
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
    query = request.args.get('query')
    if query:
        products = Product.query.filter(Product.name.like(f"%{query}%")).order_by(Product.expiration_date.asc()).all()
    else:
        products = Product.query.order_by(Product.expiration_date.asc()).all()
    for product in products:
        product.days_left = calculate_days_left(product.expiration_date)
    return render_template('list.html', products=products, datetime=datetime)


# Belirli tarihler arasında son kullanma tarihi olan ürünleri listeleme
@app.route('/expired', methods=['GET', 'POST'])
def expired_products():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        products = Product.query.filter(Product.expiration_date.between(start_date, end_date)).all()
        for product in products:
            product.days_left = calculate_days_left(product.expiration_date)
        return render_template('expired.html', products=products)
    return render_template('expired.html', products=[])


# Ürünü silme
@app.route('/delete/<int:id>', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!')
    return redirect(url_for('list_products'))


# Belirli tarihler arasında olan ürünleri silme
@app.route('/delete_by_date', methods=['GET', 'POST'])
def delete_by_date():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        products = Product.query.filter(Product.expiration_date.between(start_date, end_date)).all()
        for product in products:
            db.session.delete(product)
        db.session.commit()
        flash('Products deleted successfully!')
        return redirect(url_for('delete_by_date'))
    return render_template('delete_by_date.html')


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

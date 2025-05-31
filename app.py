from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for
import mysql.connector
import bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import BaseForm as FlaskAdminForm
from wtforms import StringField, PasswordField, SelectField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Email, Optional
from flask_cors import CORS
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
import os
from flask_admin.form import ImageUploadField
from flask_admin.model.form import InlineFormAdmin
from flask_admin.form.widgets import Select2Widget

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key_here'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:tanami2804@localhost/CuaHangThietBiDienTu'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_URL'] = '/static/uploads/'

db = SQLAlchemy(app)

# Cấu hình kết nối cơ sở dữ liệu
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tanami2804',
    'database': 'CuaHangThietBiDienTu',
    'charset': 'utf8mb4'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Đăng ký
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    phone = data.get('phone')

    if not username or not password:
        return jsonify({'error': 'Thiếu thông tin tên đăng nhập hoặc mật khẩu'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM NguoiDung WHERE TenDangNhap = %s', (username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Tên đăng nhập đã tồn tại'}), 400

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        'INSERT INTO NguoiDung (TenDangNhap, MatKhau, VaiTro, Ho, Ten, SoDienThoai) VALUES (%s, %s, %s, %s, %s, %s)',
        (username, hashed, 'khachhang', lastname, firstname, phone)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Đăng ký thành công'}), 201

# Đăng nhập
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM NguoiDung WHERE TenDangNhap = %s', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        return jsonify({'error': 'Tên đăng nhập hoặc mật khẩu không đúng'}), 401

    try:
        stored_password = user['MatKhau'].encode('utf-8') if isinstance(user['MatKhau'], str) else user['MatKhau']
        if bcrypt.checkpw(password.encode('utf-8'), stored_password):
            session['user_id'] = user['MaNguoiDung']
            session['username'] = user['TenDangNhap']
            session['role'] = user['VaiTro']
            # Phân quyền chuyển hướng
            if user['VaiTro'] == 'admin':
                redirect_url = '/admin'
            else:
                redirect_url = '/index.html'
            return jsonify({
                'message': 'Đăng nhập thành công',
                'user': {
                    'id': user['MaNguoiDung'],
                    'username': user['TenDangNhap'],
                    'role': user['VaiTro']
                },
                'redirect_url': redirect_url
            })
    except Exception as e:
        print(f"Lỗi xác thực mật khẩu: {str(e)}")
        return jsonify({'error': 'Lỗi xác thực mật khẩu'}), 500

    return jsonify({'error': 'Tên đăng nhập hoặc mật khẩu không đúng'}), 401

# Lấy danh sách sản phẩm
@app.route('/api/products')
def get_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT MaSanPham, TenSanPham, Gia, SoLuongTon, AnhSanPham FROM SanPham')
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(products)

# Thêm vào giỏ hàng
@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    # Kiểm tra sản phẩm tồn tại
    cursor.execute('SELECT SoLuongTon FROM SanPham WHERE MaSanPham = %s', (product_id,))
    row = cursor.fetchone()
    if not row or row[0] < quantity:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Sản phẩm không đủ số lượng'}), 400
    # Kiểm tra đã có trong giỏ chưa
    cursor.execute('SELECT SoLuong FROM GioHang WHERE MaNguoiDung = %s AND MaSanPham = %s', (user_id, product_id))
    item = cursor.fetchone()
    if item:
        cursor.execute('UPDATE GioHang SET SoLuong = SoLuong + %s WHERE MaNguoiDung = %s AND MaSanPham = %s', (quantity, user_id, product_id))
    else:
        cursor.execute('INSERT INTO GioHang (MaNguoiDung, MaSanPham, SoLuong) VALUES (%s, %s, %s)', (user_id, product_id, quantity))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Thêm vào giỏ hàng thành công'})

# Xem giỏ hàng
@app.route('/api/cart', methods=['GET'])
def get_cart():
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''SELECT g.MaGioHang, g.MaSanPham, s.TenSanPham, g.SoLuong, s.Gia FROM GioHang g JOIN SanPham s ON g.MaSanPham = s.MaSanPham WHERE g.MaNguoiDung = %s''', (user_id,))
    cart = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(cart)

# Đặt hàng
@app.route('/api/orders', methods=['POST'])
def create_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    # Lấy giỏ hàng
    cursor.execute('SELECT MaSanPham, SoLuong FROM GioHang WHERE MaNguoiDung = %s', (user_id,))
    cart_items = cursor.fetchall()
    if not cart_items:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Giỏ hàng trống'}), 400
    # Tính tổng tiền
    total = 0
    for item in cart_items:
        cursor.execute('SELECT Gia, SoLuongTon FROM SanPham WHERE MaSanPham = %s', (item[0],))
        product = cursor.fetchone()
        if not product or product[1] < item[1]:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Sản phẩm không đủ số lượng'}), 400
        total += float(product[0]) * item[1]
    # Tạo đơn hàng
    cursor.execute('INSERT INTO DonHang (MaNguoiDung, TongTien) VALUES (%s, %s)', (user_id, total))
    order_id = cursor.lastrowid
    # Thêm chi tiết đơn hàng và cập nhật kho
    for item in cart_items:
        cursor.execute('SELECT Gia FROM SanPham WHERE MaSanPham = %s', (item[0],))
        price = cursor.fetchone()[0]
        cursor.execute('INSERT INTO ChiTietDonHang (MaDonHang, MaSanPham, SoLuong, DonGia) VALUES (%s, %s, %s, %s)', (order_id, item[0], item[1], price))
        cursor.execute('UPDATE SanPham SET SoLuongTon = SoLuongTon - %s WHERE MaSanPham = %s', (item[1], item[0]))
    # Xóa giỏ hàng
    cursor.execute('DELETE FROM GioHang WHERE MaNguoiDung = %s', (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Đặt hàng thành công', 'order_id': order_id})

# Xem đơn hàng
@app.route('/api/orders', methods=['GET'])
def get_orders():
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy đơn hàng của người dùng
    cursor.execute('''
        SELECT
            dh.MaDonHang, dh.MaNguoiDung, dh.NgayDat, dh.TongTien,
            nd.Ho, nd.Ten, nd.SoDienThoai
        FROM DonHang dh
        JOIN NguoiDung nd ON dh.MaNguoiDung = nd.MaNguoiDung
        WHERE dh.MaNguoiDung = %s
        ORDER BY dh.NgayDat DESC -- Sắp xếp theo ngày, mới nhất trước
    ''', (user_id,))
    orders = cursor.fetchall()

    # Lấy chi tiết cho từng đơn hàng
    for order in orders:
        cursor.execute('''
            SELECT
                c.MaSanPham, s.TenSanPham, c.SoLuong, c.DonGia,
                s.AnhSanPham
            FROM ChiTietDonHang c
            JOIN SanPham s ON c.MaSanPham = s.MaSanPham
            WHERE c.MaDonHang = %s
        ''', (order['MaDonHang'],))
        order['items'] = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(orders)

# Models
class NguoiDung(db.Model):
    __tablename__ = 'NguoiDung'
    MaNguoiDung = db.Column(db.Integer, primary_key=True)
    TenDangNhap = db.Column(db.String(50), unique=True, nullable=False)
    MatKhau = db.Column(db.String(100), nullable=False)
    VaiTro = db.Column(db.Enum('admin', 'khachhang'), default='khachhang')
    Ho = db.Column(db.String(50))
    Ten = db.Column(db.String(50))
    SoDienThoai = db.Column(db.String(20))

class LoaiSanPham(db.Model):
    __tablename__ = 'LoaiSanPham'
    MaLoai = db.Column(db.Integer, primary_key=True)
    TenLoai = db.Column(db.String(50), nullable=False)

class SanPham(db.Model):
    __tablename__ = 'SanPham'
    MaSanPham = db.Column(db.Integer, primary_key=True)
    TenSanPham = db.Column(db.String(100), nullable=False)
    MaLoai = db.Column(db.Integer, db.ForeignKey('LoaiSanPham.MaLoai'))
    Gia = db.Column(db.Numeric(10, 2), nullable=False)
    SoLuongTon = db.Column(db.Integer, default=0)
    AnhSanPham = db.Column(db.String(255))
    loaisanpham = db.relationship('LoaiSanPham', backref='sanpham')

class DonHang(db.Model):
    __tablename__ = 'DonHang'
    MaDonHang = db.Column(db.Integer, primary_key=True)
    MaNguoiDung = db.Column(db.Integer, db.ForeignKey('NguoiDung.MaNguoiDung'))
    NgayDat = db.Column(db.DateTime)
    TongTien = db.Column(db.Numeric(10, 2))

class ChiTietDonHang(db.Model):
    __tablename__ = 'ChiTietDonHang'
    MaChiTiet = db.Column(db.Integer, primary_key=True)
    MaDonHang = db.Column(db.Integer, db.ForeignKey('DonHang.MaDonHang'))
    MaSanPham = db.Column(db.Integer, db.ForeignKey('SanPham.MaSanPham'))
    SoLuong = db.Column(db.Integer, nullable=False)
    DonGia = db.Column(db.Numeric(10, 2), nullable=False)

# Form cho NguoiDungAdminView
class NguoiDungForm(FlaskAdminForm):
    TenDangNhap = StringField('Tên Đăng Nhập', [DataRequired()])
    MatKhau = PasswordField('Mật Khẩu', [Optional()])
    VaiTro = SelectField('Vai Trò', choices=[('admin', 'Admin'), ('khachhang', 'Khách Hàng')], validators=[DataRequired()])
    # Thêm các trường mới
    Ho = StringField('Họ')
    Ten = StringField('Tên')
    SoDienThoai = StringField('Số Điện Thoại')

# Custom ModelView cho NguoiDung
class NguoiDungAdminView(ModelView):
    form = NguoiDungForm
    column_list = ('MaNguoiDung', 'TenDangNhap', 'VaiTro', 'Ho', 'Ten', 'SoDienThoai')
    column_labels = dict(MaNguoiDung='Mã Người Dùng', TenDangNhap='Tên Đăng Nhập', MatKhau='Mật Khẩu', VaiTro='Vai Trò', Ho='Họ', Ten='Tên', SoDienThoai='Số Điện Thoại')
    form_columns = ('TenDangNhap', 'MatKhau', 'VaiTro', 'Ho', 'Ten', 'SoDienThoai')

    def on_model_change(self, form, model, is_created):
        if form.MatKhau.data:
            # Mã hóa mật khẩu và lưu vào model
            hashed = bcrypt.hashpw(form.MatKhau.data.encode('utf-8'), bcrypt.gensalt())
            model.MatKhau = hashed.decode('utf-8')

    def create_model(self, form):
        if not form.MatKhau.data:
            raise ValueError("Mật khẩu không được để trống khi tạo người dùng mới.")
        return super(NguoiDungAdminView, self).create_model(form)

    def update_model(self, form, model):
        if form.MatKhau.data:
            # Mã hóa mật khẩu mới
            hashed = bcrypt.hashpw(form.MatKhau.data.encode('utf-8'), bcrypt.gensalt())
            model.MatKhau = hashed.decode('utf-8')
        return super(NguoiDungAdminView, self).update_model(form, model)

# Custom AdminIndexView để kiểm tra quyền
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('role') == 'admin':
            # Chuyển hướng về trang login.html nếu không phải admin
            return redirect(url_for('serve_login_html'))
        return super(MyAdminIndexView, self).index()

# Flask-Admin
admin = Admin(app, name='TanamiTechS Admin', template_mode='bootstrap4', index_view=MyAdminIndexView(endpoint='admin_index', url='/admin'))

# Thêm View cho NguoiDung
admin.add_view(ModelView(NguoiDung, db.session))

# Thêm View cho LoaiSanPham
admin.add_view(ModelView(LoaiSanPham, db.session, endpoint='loaisanpham_admin'))

# Form cho SanPham
class SanPhamForm(FlaskAdminForm):
    TenSanPham = StringField('Tên Sản Phẩm', validators=[DataRequired()])
    MaLoai = SelectField('Loại Sản Phẩm', coerce=int, choices=[])
    Gia = DecimalField('Giá', validators=[DataRequired()])
    SoLuongTon = IntegerField('Số Lượng Tồn', validators=[DataRequired()])
    AnhSanPham_File = ImageUploadField(
        'Tải ảnh lên',
        base_path=UPLOAD_FOLDER,
        url_relative_path=app.config['UPLOAD_URL'],
        allowed_extensions=('jpg', 'jpeg', 'png', 'gif'),
        max_size=(1024 * 1024 * 5, 1024 * 1024),
        thumbnail_size=(100, 100, True),
        thumbnail_filter=PIL.Image.LANCZOS,
        image_filter=PIL.Image.LANCZOS
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tải động các lựa chọn cho Loại Sản Phẩm
        with app.app_context():
            loai_san_pham = LoaiSanPham.query.all()
            self.MaLoai.choices = [(l.MaLoai, l.TenLoai) for l in loai_san_pham]

# Custom ModelView cho SanPham
class SanPhamAdminView(ModelView):
    form = SanPhamForm
    column_list = ('MaSanPham', 'TenSanPham', 'loaisanpham', 'Gia', 'SoLuongTon', 'AnhSanPham')
    column_labels = dict(MaSanPham='Mã SP', TenSanPham='Tên SP', loaisanpham='Loại SP', Gia='Giá', SoLuongTon='Số lượng', AnhSanPham='Ảnh SP')
    column_searchable_list = ('TenSanPham', 'loaisanpham.TenLoai')
    column_filters = ('loaisanpham.TenLoai',)

    # Kiểm tra quyền truy cập
    def is_accessible(self):
        return session.get('role') == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('serve_login_html'))

    def on_model_change(self, form, model, is_created):
        # Xử lý tải ảnh lên
        if form.AnhSanPham_File.data and hasattr(form.AnhSanPham_File.data, 'filename'):
            filename = os.path.basename(form.AnhSanPham_File.data.filename)
            model.AnhSanPham = app.config['UPLOAD_URL'] + filename
        elif not is_created and not form.AnhSanPham_File.data and model.AnhSanPham and model.AnhSanPham.startswith(app.config['UPLOAD_URL']):
             pass
        elif not form.AnhSanPham_File.data:
             model.AnhSanPham = None

    # Xử lý sau khi xóa model
    def after_model_delete(self, model):
        if model.AnhSanPham and model.AnhSanPham.startswith(app.config['UPLOAD_URL']):
            file_name = os.path.basename(model.AnhSanPham)
            file_path = os.path.join(UPLOAD_FOLDER, file_name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Đã xóa file ảnh: {file_path}")
                except Exception as e:
                    print(f"Lỗi khi xóa file ảnh {file_path}: {e}")


admin.add_view(SanPhamAdminView(SanPham, db.session, endpoint='sanpham_admin'))

admin.add_view(ModelView(DonHang, db.session, endpoint='donhang_admin'))
admin.add_view(ModelView(ChiTietDonHang, db.session, endpoint='chitietdonhang_admin'))

# Route index
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/index.html')
def serve_index_html():
    return send_from_directory('.', 'index.html')

# Route login
@app.route('/login.html')
def serve_login_html():
    return send_from_directory('.', 'login.html')

# Route static files
@app.route('/assets/<path:filename>')
def serve_static(filename):
    return send_from_directory('assets', filename)

# Lấy thông tin người dùng
@app.route('/api/user', methods=['GET'])
def get_user():
    if 'user_id' in session:
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT MaNguoiDung, TenDangNhap, VaiTro, Ho, Ten, SoDienThoai FROM NguoiDung WHERE MaNguoiDung = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            display_name = f"{user.get('Ten', '')} {user.get('Ho', '')}".strip()
            if not display_name:
                 display_name = user.get('TenDangNhap')

            return jsonify({
                'isLoggedIn': True,
                'user': {
                    'id': user['MaNguoiDung'],
                    'username': user['TenDangNhap'],
                    'role': user['VaiTro'],
                    'name': display_name
                }
            })
        else:
            session.pop('user_id', None)
            session.pop('username', None)
            session.pop('role', None)
            return jsonify({'isLoggedIn': False}), 401
    else:
        return jsonify({'isLoggedIn': False})

# Endpoint đăng xuất
@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    return jsonify({'message': 'Đăng xuất thành công'}), 200

# LogoutView Admin
class LogoutView(BaseView):
    @expose('/')
    def index(self):
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('role', None)
        return redirect(url_for('serve_login_html'))

    def is_accessible(self):
        return 'user_id' in session

# LogoutView
admin.add_view(LogoutView(name='Đăng xuất', endpoint='admin_logout', category=''))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
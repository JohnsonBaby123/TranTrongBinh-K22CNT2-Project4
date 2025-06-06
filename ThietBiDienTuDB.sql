CREATE DATABASE CuaHangThietBiDienTu;
USE CuaHangThietBiDienTu;

CREATE TABLE NguoiDung (
    MaNguoiDung INT AUTO_INCREMENT PRIMARY KEY,
    TenDangNhap VARCHAR(50) NOT NULL UNIQUE,
    MatKhau VARCHAR(100) NOT NULL,
    VaiTro ENUM('admin', 'khachhang') DEFAULT 'khachhang',
    Ho VARCHAR(50),
    Ten VARCHAR(50),
    SoDienThoai VARCHAR(20)
);
CREATE TABLE LoaiSanPham (
    MaLoai INT AUTO_INCREMENT PRIMARY KEY,
    TenLoai VARCHAR(50) NOT NULL
);
CREATE TABLE SanPham (
    MaSanPham INT AUTO_INCREMENT PRIMARY KEY,
    TenSanPham VARCHAR(100) NOT NULL,
    MaLoai INT,
    Gia DECIMAL(10,2) NOT NULL,
    SoLuongTon INT DEFAULT 0,
    AnhSanPham VARCHAR(255),
    FOREIGN KEY (MaLoai) REFERENCES LoaiSanPham(MaLoai)
);
CREATE TABLE DonHang (
    MaDonHang INT AUTO_INCREMENT PRIMARY KEY,
    MaNguoiDung INT,
    NgayDat DATETIME DEFAULT CURRENT_TIMESTAMP,
    TongTien DECIMAL(10,2),
    FOREIGN KEY (MaNguoiDung) REFERENCES NguoiDung(MaNguoiDung)
);
CREATE TABLE ChiTietDonHang (
    MaChiTiet INT AUTO_INCREMENT PRIMARY KEY,
    MaDonHang INT,
    MaSanPham INT,
    SoLuong INT NOT NULL,
    DonGia DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (MaDonHang) REFERENCES DonHang(MaDonHang),
    FOREIGN KEY (MaSanPham) REFERENCES SanPham(MaSanPham)
);
CREATE TABLE GioHang (
    MaGioHang INT AUTO_INCREMENT PRIMARY KEY,
    MaNguoiDung INT,
    MaSanPham INT,
    SoLuong INT DEFAULT 1,
    NgayThem DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (MaNguoiDung) REFERENCES NguoiDung(MaNguoiDung),
    FOREIGN KEY (MaSanPham) REFERENCES SanPham(MaSanPham)
);
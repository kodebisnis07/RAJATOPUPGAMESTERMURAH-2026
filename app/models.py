from datetime import datetime
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), unique=True, nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    member_level = db.Column(db.String(30), default="Bronze")
    balance = db.Column(db.Integer, default=0)
    bonus_coins = db.Column(db.Integer, default=0)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class FavoriteGame(db.Model):
    __tablename__ = "favorite_games"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="favorite_games")
    category = db.relationship("Category", backref="favorited_by")

class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="admin")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash((password or "").strip())

    def check_password(self, password):
        password = (password or "").strip()
        stored = self.password_hash or ""
        try:
            return check_password_hash(stored, password)
        except Exception:
            # Kompatibilitas untuk database lama yang pernah menyimpan password admin sebagai teks biasa
            # atau hash lama yang tidak lagi didukung Werkzeug.
            return bool(stored and stored == password)


class CatalogSection(db.Model):
    __tablename__ = "catalog_sections"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    categories = db.relationship("Category", backref="catalog_section", lazy=True)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    icon = db.Column(db.String(255), nullable=True)
    catalog_section_id = db.Column(db.Integer, db.ForeignKey("catalog_sections.id"), nullable=True)
    badge = db.Column(db.String(60), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="category", lazy=True)
    games = db.relationship("Game", backref="category", lazy=True)


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="game", lazy=True)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=True)

    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    price_modal = db.Column(db.Integer, default=0)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0)

    provider = db.Column(db.String(100), nullable=True)
    provider_code = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="product", lazy=True)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    invoice = db.Column(db.String(100), unique=True, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    customer_name = db.Column(db.String(100), nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_phone = db.Column(db.String(30), nullable=True)

    game_user_id = db.Column(db.String(100), nullable=True)
    game_server_id = db.Column(db.String(100), nullable=True)
    game_nickname = db.Column(db.String(100), nullable=True)

    price = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(100), nullable=True)

    payment_status = db.Column(db.String(30), default="pending")
    order_status = db.Column(db.String(30), default="pending")
    payment_url = db.Column(db.String(500), nullable=True)
    payment_reference = db.Column(db.String(150), nullable=True)
    voucher_code = db.Column(db.String(60), nullable=True)
    discount_amount = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="orders")


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    payment_code = db.Column(db.String(100), nullable=True)
    payment_name = db.Column(db.String(100), nullable=True)
    provider = db.Column(db.String(50), nullable=True)
    reference = db.Column(db.String(150), nullable=True)
    checkout_url = db.Column(db.String(500), nullable=True)
    qr_url = db.Column(db.String(500), nullable=True)
    amount = db.Column(db.Integer, nullable=False)

    status = db.Column(db.String(30), default="pending")
    expired_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship("Order", backref="payment", uselist=False)


class UserNotification(db.Model):
    __tablename__ = "user_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default="info")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="notifications")
    order = db.relationship("Order", backref="notifications")


class WalletTopup(db.Model):
    __tablename__ = "wallet_topups"

    id = db.Column(db.Integer, primary_key=True)
    invoice = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    bonus_coins = db.Column(db.Integer, default=0)
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_methods.id"), nullable=True)
    payment_method_name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), default="pending")  # pending, approved, rejected, cancelled
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="wallet_topups")
    payment_method = db.relationship("PaymentMethod", backref="wallet_topups")

class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), default="bank")  # bank, ewallet, qris, virtual_account, manual
    account_number = db.Column(db.String(120), nullable=True)
    account_name = db.Column(db.String(120), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    qr_image = db.Column(db.String(255), nullable=True)
    instruction = db.Column(db.Text, nullable=True)
    admin_fee = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_offline = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def available(self):
        return bool(self.is_active and not self.is_offline)


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Banner(db.Model):
    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    tag = db.Column(db.String(80), default="RAJA TOPUP GAMES")
    image = db.Column(db.String(255), nullable=True)
    button_text = db.Column(db.String(80), default="Top Up Sekarang")
    link = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Promo(db.Model):
    __tablename__ = "promos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    badge = db.Column(db.String(60), default="PROMO")
    link = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FAQ(db.Model):
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdminActivityLog(db.Model):
    __tablename__ = "admin_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    admin_username = db.Column(db.String(100), nullable=True)
    admin_role = db.Column(db.String(30), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("Admin", backref="activity_logs")



class ChatThread(db.Model):
    __tablename__ = "chat_threads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(160), default="Bantuan Customer Service")
    status = db.Column(db.String(30), default="open")  # open, closed
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="chat_threads")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("chat_threads.id"), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # user, admin, operator, super_admin
    sender_id = db.Column(db.Integer, nullable=True)
    sender_name = db.Column(db.String(120), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read_by_user = db.Column(db.Boolean, default=False)
    is_read_by_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    thread = db.relationship("ChatThread", backref="messages")


class Voucher(db.Model):
    __tablename__ = "vouchers"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    discount_type = db.Column(db.String(20), default="fixed")  # fixed / percent
    discount_value = db.Column(db.Integer, default=0)
    min_order = db.Column(db.Integer, default=0)
    quota = db.Column(db.Integer, default=0)  # 0 = tanpa batas
    used_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_discount(self, amount):
        amount = int(amount or 0)
        if not self.is_active or amount < (self.min_order or 0):
            return 0
        if self.quota and self.used_count >= self.quota:
            return 0
        if self.discount_type == "percent":
            return min(amount, int(amount * (self.discount_value or 0) / 100))
        return min(amount, int(self.discount_value or 0))


class ResellerProfile(db.Model):
    __tablename__ = "reseller_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    store_name = db.Column(db.String(160), nullable=True)
    level = db.Column(db.String(40), default="Reseller")
    commission_percent = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default="pending")  # pending / approved / rejected
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("reseller_profile", uselist=False))


class ApiClient(db.Model):
    __tablename__ = "api_clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    domain = db.Column(db.String(255), nullable=True)
    contact_name = db.Column(db.String(120), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    key_prefix = db.Column(db.String(24), unique=True, nullable=False, index=True)
    api_key_hash = db.Column(db.String(255), nullable=False)
    api_secret_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Integer, default=0)
    price_markup_percent = db.Column(db.Integer, default=0)
    allowed_ips = db.Column(db.Text, nullable=True)
    callback_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), default="active")
    white_label_enabled = db.Column(db.Boolean, default=False)
    brand_name = db.Column(db.String(160), nullable=True)
    brand_logo = db.Column(db.String(255), nullable=True)
    brand_primary_color = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_api_key(self, raw_key):
        self.api_key_hash = generate_password_hash(raw_key)

    def check_api_key(self, raw_key):
        return check_password_hash(self.api_key_hash, raw_key)

    def set_api_secret(self, raw_secret):
        self.api_secret_hash = generate_password_hash(raw_secret)

    def check_api_secret(self, raw_secret):
        return check_password_hash(self.api_secret_hash, raw_secret)


class ApiOrder(db.Model):
    __tablename__ = "api_orders"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("api_clients.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    external_ref = db.Column(db.String(120), nullable=False)
    charged_amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("ApiClient", backref="api_orders")
    order = db.relationship("Order", backref=db.backref("api_order", uselist=False))
    __table_args__ = (db.UniqueConstraint("client_id", "external_ref", name="uq_api_client_external_ref"),)


class ApiRequestLog(db.Model):
    __tablename__ = "api_request_logs"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("api_clients.id"), nullable=True)
    method = db.Column(db.String(10), nullable=False)
    endpoint = db.Column(db.String(255), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    ip_address = db.Column(db.String(80), nullable=True)
    response_message = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("ApiClient", backref="request_logs")

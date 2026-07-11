import os
import secrets
import hashlib
from datetime import datetime
from urllib.parse import urlencode
from flask import Blueprint, render_template, request, redirect, session, url_for, flash, current_app, jsonify
from app.extensions import db
from app.models import User, Order, FavoriteGame, Category, UserNotification, PaymentMethod, WalletTopup, ChatThread, ChatMessage
from app.utils import save_uploaded_image
from app.email_service import send_password_reset_email
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


def _password_reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="user-password-reset")


def _password_fingerprint(user):
    # Membuat token lama otomatis tidak berlaku setelah password diganti.
    return hashlib.sha256((user.password_hash or "").encode("utf-8")).hexdigest()[:20]


def _make_reset_token(user):
    return _password_reset_serializer().dumps({
        "user_id": user.id,
        "email": user.email,
        "password_fingerprint": _password_fingerprint(user),
    })


def _load_user_from_token(token, max_age=None):
    max_age = max_age or current_app.config.get("PASSWORD_RESET_MAX_AGE", 3600)
    try:
        data = _password_reset_serializer().loads(token, max_age=max_age)
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"

    user = User.query.get(data.get("user_id"))
    if (not user or user.email != data.get("email") or not user.is_active
            or data.get("password_fingerprint") != _password_fingerprint(user)):
        return None, "invalid"
    return user, None


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _normalize_phone(phone):
    return (phone or "").strip().replace(" ", "").replace("-", "")


def _normalize_username(username):
    return (username or "").strip().lower()


def _username_is_valid(username):
    return bool(username) and 4 <= len(username) <= 30 and all(ch.isalnum() or ch in "._-" for ch in username)


def _current_user():
    if not session.get("user_id"):
        return None
    return User.query.get(session.get("user_id"))


def _require_user():
    user = _current_user()
    if not user:
        flash("Silakan login dulu untuk membuka profil akun.", "error")
        return None
    return user


def _avatar_url(user):
    if user and user.avatar:
        return url_for("static", filename=f"img/avatars/{user.avatar}")
    return None


def _user_stats(user):
    orders = Order.query.filter_by(user_id=user.id)
    total_orders = orders.count()
    pending_orders = Order.query.filter_by(user_id=user.id, order_status="pending").count()
    success_orders = Order.query.filter(Order.user_id == user.id, Order.order_status.in_(["success", "completed", "done", "processing"])).count()
    cancelled_orders = Order.query.filter(Order.user_id == user.id, Order.order_status.in_(["cancelled", "failed"])).count()
    total_spent = sum((o.price or 0) for o in Order.query.filter(Order.user_id == user.id, Order.payment_status.in_(["paid", "success"])).all())
    if total_spent >= 5000000:
        level = "Platinum"
    elif total_spent >= 2000000:
        level = "Gold"
    elif total_spent >= 500000:
        level = "Silver"
    else:
        level = user.member_level or "Bronze"
    if user.member_level != level:
        user.member_level = level
        db.session.commit()
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "success_orders": success_orders,
        "cancelled_orders": cancelled_orders,
        "total_spent": total_spent,
        "member_level": level,
    }


def _bonus_coins_for_amount(amount):
    """Bonus koin otomatis berdasarkan nominal topup saldo."""
    amount = int(amount or 0)
    if amount >= 1000000:
        return 2500
    if amount >= 500000:
        return 1000
    if amount >= 250000:
        return 400
    if amount >= 100000:
        return 150
    if amount >= 50000:
        return 50
    return 0





@auth_bp.route("/register", methods=["GET", "POST"])
@auth_bp.route("/daftar", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        username = _normalize_username(request.form.get("username"))
        email = (request.form.get("email") or "").strip().lower()
        phone = _normalize_phone(request.form.get("phone"))
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        context = {"name": name, "username": username, "email": email, "phone": phone}

        if not name or not username or not email or not phone or not password or not confirm_password:
            flash("Semua data wajib diisi.", "error")
            return render_template("auth/register.html", **context)

        if not _username_is_valid(username):
            flash("Username harus 4-30 karakter dan hanya boleh huruf, angka, titik, underscore, atau strip.", "error")
            return render_template("auth/register.html", **context)

        if len(password) < 6:
            flash("Password minimal 6 karakter.", "error")
            return render_template("auth/register.html", **context)

        if password != confirm_password:
            flash("Konfirmasi password tidak sama.", "error")
            return render_template("auth/register.html", **context)

        if User.query.filter_by(username=username).first():
            flash("Username sudah dipakai. Silakan gunakan username lain.", "error")
            return render_template("auth/register.html", **context)

        if User.query.filter_by(email=email).first():
            flash("Email sudah terdaftar. Silakan login atau gunakan email lain.", "error")
            return render_template("auth/register.html", **context)

        if phone and User.query.filter_by(phone=phone).first():
            flash("Nomor WhatsApp sudah terdaftar. Silakan gunakan nomor lain.", "error")
            return render_template("auth/register.html", **context)

        user = User(
            name=name,
            username=username,
            email=email,
            phone=phone,
            role="user",
            is_active=True,
            member_level="Bronze",
            balance=0,
            bonus_coins=0,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["username"] = user.username
        session["user_email"] = user.email
        session["user_phone"] = user.phone
        flash("Pendaftaran berhasil. Akun Anda sudah aktif.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = _normalize_username(request.form.get("username"))
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, is_active=True).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["username"] = user.username
            session["user_email"] = user.email
            session["user_phone"] = user.phone
            flash("Login berhasil.", "success")
            return redirect(url_for("auth.dashboard"))

        flash("Username atau password salah.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/lupa-password", methods=["GET", "POST"])
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email, is_active=True).first()
        if user:
            token = _make_reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            sent, error = send_password_reset_email(
                user,
                reset_url,
                expires_minutes=max(1, int(current_app.config.get("PASSWORD_RESET_MAX_AGE", 3600)) // 60),
            )
            if not sent:
                current_app.logger.error("Gagal mengirim email reset password ke %s: %s", email, error)
                # Link tidak ditampilkan ke pengunjung agar akun tetap aman.
            else:
                current_app.logger.info("Email reset password berhasil dikirim ke %s", email)

        # Respons selalu sama untuk mencegah orang menebak email yang terdaftar.
        flash("Jika email tersebut terdaftar, kami sudah mengirim link untuk membuat password baru. Periksa folder Inbox atau Spam.", "success")
        return redirect(url_for("auth.forgot_password"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user, error = _load_user_from_token(token)
    if error == "expired":
        flash("Link reset password sudah kedaluwarsa. Silakan minta link baru.", "error")
        return redirect(url_for("auth.forgot_password"))
    if error:
        flash("Link reset password tidak valid.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(password) < 6:
            flash("Password minimal 6 karakter.", "error")
            return render_template("auth/reset_password.html", token=token)
        if password != confirm_password:
            flash("Konfirmasi password tidak sama.", "error")
            return render_template("auth/reset_password.html", token=token)
        user.set_password(password)
        db.session.commit()
        flash("Password berhasil diubah. Silakan login dengan password baru.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/dashboard")
@auth_bp.route("/akun")
def dashboard():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    latest_orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(5).all()
    favorites = FavoriteGame.query.filter_by(user_id=user.id).order_by(FavoriteGame.created_at.desc()).limit(6).all()
    return render_template("auth/dashboard.html", user=user, stats=_user_stats(user), orders=latest_orders, favorites=favorites, avatar_url=_avatar_url(user))


@auth_bp.route("/profil")
@auth_bp.route("/profile")
def profile():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    latest_orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
    return render_template("auth/profile.html", user=user, stats=_user_stats(user), orders=latest_orders, avatar_url=_avatar_url(user))


@auth_bp.route("/profil/edit", methods=["GET", "POST"])
@auth_bp.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = _normalize_phone(request.form.get("phone"))
        if not name or not email or not phone:
            flash("Nama, email, dan nomor telepon wajib diisi.", "error")
            return redirect(url_for("auth.edit_profile"))
        if User.query.filter(User.email == email, User.id != user.id).first():
            flash("Email sudah dipakai akun lain.", "error")
            return redirect(url_for("auth.edit_profile"))
        if User.query.filter(User.phone == phone, User.id != user.id).first():
            flash("Nomor telepon sudah dipakai akun lain.", "error")
            return redirect(url_for("auth.edit_profile"))
        try:
            avatar_name = save_uploaded_image(request.files.get("avatar"), current_app.config["AVATAR_UPLOAD_FOLDER"])
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("auth.edit_profile"))
        if avatar_name:
            if user.avatar:
                old_path = os.path.join(current_app.config["AVATAR_UPLOAD_FOLDER"], user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)
            user.avatar = avatar_name
        if request.form.get("remove_avatar") == "1" and user.avatar:
            old_path = os.path.join(current_app.config["AVATAR_UPLOAD_FOLDER"], user.avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
            user.avatar = None
        user.name = name
        user.email = email
        user.phone = phone
        db.session.commit()
        session["user_name"] = user.name
        session["user_phone"] = user.phone
        flash("Profil berhasil diperbarui.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/edit_profile.html", user=user, avatar_url=_avatar_url(user))


@auth_bp.route("/profil/password", methods=["GET", "POST"])
@auth_bp.route("/profile/password", methods=["GET", "POST"])
def change_password():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not current_password or not user.check_password(current_password):
            flash("Password lama salah.", "error")
            return redirect(url_for("auth.change_password"))
        if len(new_password) < 6:
            flash("Password baru minimal 6 karakter.", "error")
            return redirect(url_for("auth.change_password"))
        if new_password != confirm_password:
            flash("Konfirmasi password baru tidak sama.", "error")
            return redirect(url_for("auth.change_password"))
        user.set_password(new_password)
        db.session.commit()
        flash("Password berhasil diubah.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/change_password.html", user=user)


@auth_bp.route("/pesanan")
@auth_bp.route("/orders")
@auth_bp.route("/invoice")
def orders():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    status = request.args.get("status", "").strip()
    query = Order.query.filter_by(user_id=user.id)
    if status:
        query = query.filter((Order.order_status == status) | (Order.payment_status == status))
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template("auth/orders.html", user=user, orders=orders, status=status)


@auth_bp.route("/favorit", methods=["GET"])
def favorites():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    favorites = FavoriteGame.query.filter_by(user_id=user.id).order_by(FavoriteGame.created_at.desc()).all()
    categories = Category.query.filter_by(status="active").order_by(Category.name.asc()).all()
    favorite_ids = {fav.category_id for fav in favorites}
    return render_template("auth/favorites.html", user=user, favorites=favorites, categories=categories, favorite_ids=favorite_ids)


@auth_bp.route("/favorit/<int:category_id>/toggle", methods=["POST"])
def toggle_favorite(category_id):
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    category = Category.query.get_or_404(category_id)
    existing = FavoriteGame.query.filter_by(user_id=user.id, category_id=category.id).first()
    if existing:
        db.session.delete(existing)
        flash(f"{category.name} dihapus dari favorit.", "success")
    else:
        db.session.add(FavoriteGame(user_id=user.id, category_id=category.id))
        flash(f"{category.name} ditambahkan ke favorit.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("auth.favorites"))


@auth_bp.route("/notifikasi")
@auth_bp.route("/notifications")
@auth_bp.route("/inbox")
def notifications():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    notifications = (
        UserNotification.query
        .filter_by(user_id=user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(100)
        .all()
    )
    unread = UserNotification.query.filter_by(user_id=user.id, is_read=False).all()
    for item in unread:
        item.is_read = True
    if unread:
        db.session.commit()
    return render_template("auth/notifications.html", user=user, notifications=notifications)


@auth_bp.route("/notifikasi/<int:notification_id>/baca", methods=["POST"])
def mark_notification_read(notification_id):
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    notification = UserNotification.query.filter_by(id=notification_id, user_id=user.id).first_or_404()
    notification.is_read = True
    db.session.commit()
    if notification.order:
        return redirect(url_for("home.checkout", invoice=notification.order.invoice))
    return redirect(url_for("auth.notifications"))



def _get_or_create_chat_thread(user):
    thread = ChatThread.query.filter_by(user_id=user.id, status="open").order_by(ChatThread.updated_at.desc()).first()
    if not thread:
        thread = ChatThread(user_id=user.id, subject=f"Chat bantuan - {user.username or user.name}")
        db.session.add(thread)
        db.session.commit()
    return thread


def _chat_message_payload(messages):
    return [
        {
            "id": msg.id,
            "sender_type": msg.sender_type,
            "sender_name": msg.sender_name or msg.sender_type,
            "message": msg.message,
            "created_at": msg.created_at.strftime("%d/%m/%Y %H:%M"),
        }
        for msg in messages
    ]


@auth_bp.route("/chat", methods=["GET", "POST"])
def live_chat():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    thread = _get_or_create_chat_thread(user)
    if request.method == "POST":
        message = (request.form.get("message") or "").strip()
        if not message:
            flash("Pesan tidak boleh kosong.", "error")
            return redirect(url_for("auth.live_chat"))
        msg = ChatMessage(
            thread_id=thread.id,
            sender_type="user",
            sender_id=user.id,
            sender_name=user.name or user.username,
            message=message,
            is_read_by_user=True,
            is_read_by_admin=False,
        )
        thread.status = "open"
        thread.last_message_at = datetime.utcnow()
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for("auth.live_chat"))

    admin_messages = ChatMessage.query.filter_by(thread_id=thread.id).filter(ChatMessage.sender_type != "user").all()
    changed = False
    for msg in admin_messages:
        if not msg.is_read_by_user:
            msg.is_read_by_user = True
            changed = True
    if changed:
        db.session.commit()
    messages = ChatMessage.query.filter_by(thread_id=thread.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template("auth/chat.html", user=user, thread=thread, messages=messages)


@auth_bp.route("/chat/messages")
def live_chat_messages():
    user = _require_user()
    if not user:
        return jsonify({"ok": False, "messages": []}), 401
    thread = _get_or_create_chat_thread(user)
    messages = ChatMessage.query.filter_by(thread_id=thread.id).order_by(ChatMessage.created_at.asc()).all()
    return jsonify({"ok": True, "messages": _chat_message_payload(messages)})

@auth_bp.route("/saldo", methods=["GET", "POST"])
@auth_bp.route("/topup-saldo", methods=["GET", "POST"])
def wallet_topup():
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))

    payment_methods = PaymentMethod.query.filter_by(is_active=True, is_offline=False).order_by(PaymentMethod.sort_order.asc(), PaymentMethod.name.asc()).all()

    if request.method == "POST":
        raw_amount = request.form.get("amount", "0").replace(".", "").replace(",", "").strip()
        payment_method_id = request.form.get("payment_method_id")
        try:
            amount = int(raw_amount)
        except ValueError:
            amount = 0

        if amount < 20000:
            flash("Minimal top up saldo adalah Rp20.000.", "error")
            return redirect(url_for("auth.wallet_topup"))

        method = PaymentMethod.query.filter_by(id=payment_method_id, is_active=True, is_offline=False).first() if payment_method_id else None
        if not method:
            flash("Pilih metode pembayaran yang tersedia.", "error")
            return redirect(url_for("auth.wallet_topup"))

        bonus = _bonus_coins_for_amount(amount)
        invoice = "SALDO" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        trx = WalletTopup(
            invoice=invoice,
            user_id=user.id,
            amount=amount,
            bonus_coins=bonus,
            payment_method_id=method.id,
            payment_method_name=method.name,
            status="pending",
        )
        db.session.add(trx)
        db.session.add(UserNotification(
            user_id=user.id,
            title="Top up saldo dibuat",
            message=f"Top up saldo {invoice} sebesar Rp {amount:,} menunggu konfirmasi admin. Bonus koin: {bonus}.",
            type="wallet_topup",
        ))
        db.session.commit()
        flash("Permintaan top up saldo berhasil dibuat. Silakan lakukan pembayaran dan tunggu konfirmasi admin.", "success")
        return redirect(url_for("auth.wallet_topup"))

    history = WalletTopup.query.filter_by(user_id=user.id).order_by(WalletTopup.created_at.desc()).limit(30).all()
    return render_template("auth/wallet_topup.html", user=user, payment_methods=payment_methods, history=history, bonus_preview=_bonus_coins_for_amount)


@auth_bp.route("/saldo/<invoice>/cancel", methods=["POST"])
def cancel_wallet_topup(invoice):
    user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))
    trx = WalletTopup.query.filter_by(invoice=invoice, user_id=user.id).first_or_404()
    if trx.status != "pending":
        flash("Top up saldo ini tidak bisa dibatalkan karena sudah diproses.", "error")
        return redirect(url_for("auth.wallet_topup"))
    trx.status = "cancelled"
    db.session.add(UserNotification(
        user_id=user.id,
        title="Top up saldo dibatalkan",
        message=f"Top up saldo {trx.invoice} berhasil dibatalkan.",
        type="wallet_cancelled",
    ))
    db.session.commit()
    flash("Top up saldo berhasil dibatalkan.", "success")
    return redirect(url_for("auth.wallet_topup"))


@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_phone", None)
    flash("Anda sudah logout.", "success")
    return redirect(url_for("home.index"))

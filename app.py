from flask import Flask, render_template, request, redirect, url_for, abort, flash, session
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, Message, SiteSettings
from functools import wraps
from flask_babel import Babel, gettext as _

VISITOR_COUNT_FILE = 'visitor_count.txt'

def get_visitor_count():
    if not os.path.exists(VISITOR_COUNT_FILE):
        with open(VISITOR_COUNT_FILE, 'w') as f:
            f.write('0')
    with open(VISITOR_COUNT_FILE, 'r') as f:
        return int(f.read())

def save_visitor_count(count):
    with open(VISITOR_COUNT_FILE, 'w') as f:
        f.write(str(count))

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///factory.db'
db.init_app(app)

# --- إعداد Flask-Babel للدعم اللغوي ---
app.config['BABEL_DEFAULT_LOCALE'] = 'ar'  # اللغة الافتراضية: العربية
app.config['BABEL_SUPPORTED_LOCALES'] = ['ar', 'en']  # اللغات المدعومة

babel = Babel(app)  # إنشاء كائن Babel

# استخدم الديكوريتور مع أقواس () لضمان التوافق مع بعض الإصدارات
@babel.localeselector
def get_locale():
    # اختيار اللغة حسب الجلسة أولًا
    lang = session.get('lang')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        return lang
    # أو اختيار اللغة حسب المتصفح
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])
@app.context_processor
def inject_locale():
    return {'get_locale': get_locale}

@app.route('/change_lang/<lang>')
def change_lang(lang):
    if lang not in app.config['BABEL_SUPPORTED_LOCALES']:
        lang = 'ar'  # افتراضي إلى العربية
    session['lang'] = lang
    # إعادة التوجيه للصفحة السابقة أو الصفحة الرئيسية
    next_page = request.referrer or url_for('home')
    return redirect(next_page)

UPLOAD_FOLDER = 'static/img'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_now():
    # هذا يمكن القوالب من استخدام now() لعرض الوقت الحالي
    return {'now': datetime.now}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user') != 'admin':
            flash(_('يرجى تسجيل الدخول أولاً'), 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# بيانات مبدئية مع دعم الترجمة (gettext) للنصوص
products = [
    {"id": 1, "name": _("تمر العجوة"), "description": _("تمر عالي الجودة من المدينة"), "price": 50, "image": "ajwa.jpg"},
    {"id": 2, "name": _("تمر خلاص"), "description": _("تمر مميز بنكهة لذيذة"), "price": 40, "image": "khalas.jpg"}
]

posts = [
    {"id": 1, "title": _("فوائد التمر"), "summary": _("التمر غني بالفيتامينات"), "content": "...", "image": "date-benefits.jpg", "video": "https://www.youtube.com/embed/595WPb9ykQg"},
    {"id": 2, "title": _("تخزين التمر"), "summary": _("طرق حفظ التمور"), "content": "...", "image": "date-storage.jpg", "video": ""}
]

users = [
    {"id": 1, "username": "admin", "email": "admin@example.com"},
    {"id": 2, "username": "user1", "email": "user1@example.com"},
]

# --- باقي تعريفات الـ routes ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/products')
def products_page():
    return render_template('products.html', products=products)

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/blog')
def blog():
    return render_template('blog.html', posts=posts)

@app.route('/blog/<int:post_id>')
def blog_detail(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        abort(404)
    return render_template('blog_detail.html', post=post)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        new_msg = Message(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            content=request.form.get('content')
        )
        db.session.add(new_msg)
        db.session.commit()
        flash(_('✅ تم إرسال الرسالة بنجاح'), 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    with open('settings.json', 'r') as f:
        settings = json.load(f)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == settings['username'] and password == settings['password']:
            session['user'] = 'admin'
            return redirect(url_for('dashboard'))
        else:
            error = _('❌ اسم المستخدم أو كلمة المرور غير صحيحة.')
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash(_("تم تسجيل الخروج"), "info")
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def dashboard():
    visitor_count = get_visitor_count()
    latest_messages = Message.query.order_by(Message.timestamp.desc()).limit(5).all()
    return render_template('admin_dashboard.html',
                           total_products=len(products),
                           total_posts=len(posts),
                           total_users=len(users),
                           visitor_count=visitor_count,
                           latest_messages=latest_messages)

@app.route('/admin/users')
@login_required
def admin_users():
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
            flash(_('❌ يرجى ملء جميع الحقول'), 'danger')
            return redirect(url_for('add_user'))

        new_id = max([u['id'] for u in users]) + 1 if users else 1
        users.append({"id": new_id, "username": username, "email": email})
        flash(_('✅ تم إضافة المستخدم بنجاح'), 'success')
        return redirect(url_for('admin_users'))
    return render_template('add_user.html')

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    global users
    users = [u for u in users if u['id'] != user_id]
    flash(_('✅ تم حذف المستخدم'), 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    with open('settings.json', 'r') as f:
        settings = json.load(f)

    message = None
    if request.method == 'POST':
        settings['username'] = request.form.get('username')
        settings['password'] = request.form.get('password')
        with open('settings.json', 'w') as f:
            json.dump(settings, f)
        message = _("✅ تم حفظ التعديلات بنجاح.")
    return render_template('admin_settings.html', settings=settings, message=message)

@app.route('/admin/site-settings', methods=['GET', 'POST'])
@login_required
def admin_site_settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings(site_name=_("مصنع بادية العرب"), email="", phone="", address="", logo="")
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.site_name = request.form.get('site_name')
        settings.email = request.form.get('email')
        settings.phone = request.form.get('phone')
        settings.address = request.form.get('address')

        file = request.files.get('logo')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            settings.logo = filename

        db.session.commit()
        flash(_("✅ تم تحديث بيانات الموقع"), "success")
        return redirect(url_for('admin_site_settings'))

    return render_template('admin_site_settings.html', settings=settings)

@app.route('/admin/products')
@login_required
def admin_products():
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        file = request.files.get('image')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash(_('❌ يجب رفع صورة صحيحة للمنتج'), 'danger')
            return redirect(request.url)

        new_id = max(p['id'] for p in products) + 1 if products else 1
        products.append({"id": new_id, "name": name, "description": description, "price": float(price), "image": filename})
        flash(_('✅ تم إضافة المنتج بنجاح'), 'success')
        return redirect(url_for('admin_products'))

    return render_template('add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        abort(404)

    if request.method == 'POST':
        product['name'] = request.form.get('name')
        product['description'] = request.form.get('description')
        product['price'] = float(request.form.get('price'))

        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product['image'] = filename

        flash(_('✅ تم تحديث المنتج'), 'success')
        return redirect(url_for('admin_products'))

    return render_template('edit_product.html', product=product)

@app.route('/admin/products/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    global products
    products = [p for p in products if p['id'] != product_id]
    flash(_('✅ تم حذف المنتج'), 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/posts')
@login_required
def admin_posts():
    return render_template('admin_posts.html', posts=posts)

@app.route('/admin/posts/add', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form.get('title')
        summary = request.form.get('summary')
        content = request.form.get('content')
        video = request.form.get('video')
        file = request.files.get('image')
        filename = ''

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_id = max(p['id'] for p in posts) + 1 if posts else 1
        posts.append({"id": new_id, "title": title, "summary": summary, "content": content, "video": video, "image": filename})
        flash(_('✅ تم إضافة المقال'), 'success')
        return redirect(url_for('admin_posts'))

    return render_template('add_post.html')

@app.route('/admin/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        abort(404)

    if request.method == 'POST':
        post['title'] = request.form.get('title')
        post['summary'] = request.form.get('summary')
        post['content'] = request.form.get('content')
        post['video'] = request.form.get('video')

        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post['image'] = filename

        flash(_('✅ تم تحديث المقال'), 'success')
        return redirect(url_for('admin_posts'))

    return render_template('edit_post.html', post=post)

@app.route('/admin/posts/delete/<int:post_id>')
@login_required
def delete_post(post_id):
    global posts
    posts = [p for p in posts if p['id'] != post_id]
    flash(_('✅ تم حذف المقال'), 'info')
    return redirect(url_for('admin_posts'))

@app.before_request
def count_visitors():
    if not request.path.startswith('/admin'):
        count = get_visitor_count()
        count += 1
        save_visitor_count(count)

@app.route('/admin/messages')
@login_required
def admin_messages():
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template('admin_messages.html', messages=messages)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

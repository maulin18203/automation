from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Blueprint
import hashlib, os, time, threading
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from functools import wraps
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests as req_lib

# ─── RASPBERRY PI GPIO SETUP ─────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
    GPIO.setwarnings(False)
    GPIO_AVAILABLE = True
except ImportError:
    print("[GPIO] RPi.GPIO not available - GPIO features disabled")
    GPIO_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'brighthaven_2026_mk_secure_key')

# ─── FIREBASE ─────────────────────────────────────────────────────────────────
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── BLYNK & DEVICES ─────────────────────────────────────────────────────────
BLYNK_TOKEN = os.getenv('BLYNK_TOKEN', 'B5a6tgOxySyna1GKlB3k_ZKhhJefttXM')
BLYNK_BASE  = 'https://blynk.cloud/external/api'

# Enhanced device configuration with GPIO pins for Bedroom 1
DEVICES = {
    # Main Room
    'main_fan':    {'pin':'V0',  'room':'Main Room',  'name':'Ceiling Fan',     'icon':'bi-wind',            'type':'blynk'},
    'main_light':  {'pin':'V1',  'room':'Main Room',  'name':'Main Light',      'icon':'bi-lightbulb',       'type':'blynk'},
    'main_tv':     {'pin':'V2',  'room':'Main Room',  'name':'Television',      'icon':'bi-tv',              'type':'blynk'},
    'main_ac':     {'pin':'V3',  'room':'Main Room',  'name':'Air Conditioner', 'icon':'bi-thermometer-snow','type':'blynk'},
    
    # Bedroom 1 - Pi 4 Physical GPIO Pins (Active Low Logic)
    'bed1_light':  {'pin':32,    'room':'Bedroom 1',  'name':'Light',           'icon':'bi-lightbulb',       'type':'gpio'},
    'bed1_fan':    {'pin':36,    'room':'Bedroom 1',  'name':'Fan',             'icon':'bi-wind',            'type':'gpio'},
    'bed1_geyser': {'pin':37,    'room':'Bedroom 1',  'name':'Water Geyser',    'icon':'bi-droplet-fill',    'type':'gpio'},
    'bed1_ac':     {'pin':38,    'room':'Bedroom 1',  'name':'Air Conditioner', 'icon':'bi-thermometer-snow','type':'gpio'},
    'bed1_tv':     {'pin':40,    'room':'Bedroom 1',  'name':'TV',              'icon':'bi-tv',              'type':'gpio'},
    
    # Bedroom 2
    'bed2_light':  {'pin':'V9',  'room':'Bedroom 2',  'name':'Light',           'icon':'bi-lightbulb',       'type':'blynk'},
    'bed2_fan':    {'pin':'V10', 'room':'Bedroom 2',  'name':'Fan',             'icon':'bi-wind',            'type':'blynk'},
    'bed2_ac':     {'pin':'V11', 'room':'Bedroom 2',  'name':'Air Conditioner', 'icon':'bi-thermometer-snow','type':'blynk'},
    'bed2_tv':     {'pin':'V12', 'room':'Bedroom 2',  'name':'TV',              'icon':'bi-tv',              'type':'blynk'},
    'bed2_geyser': {'pin':'V13', 'room':'Bedroom 2',  'name':'Water Geyser',    'icon':'bi-droplet-fill',    'type':'blynk'},
    
    # Bedroom 3
    'bed3_light':  {'pin':'V14', 'room':'Bedroom 3',  'name':'Light',           'icon':'bi-lightbulb',       'type':'blynk'},
    'bed3_fan':    {'pin':'V15', 'room':'Bedroom 3',  'name':'Fan',             'icon':'bi-wind',            'type':'blynk'},
    'bed3_ac':     {'pin':'V16', 'room':'Bedroom 3',  'name':'Air Conditioner', 'icon':'bi-thermometer-snow','type':'blynk'},
    'bed3_tv':     {'pin':'V17', 'room':'Bedroom 3',  'name':'TV',              'icon':'bi-tv',              'type':'blynk'},
    'bed3_geyser': {'pin':'V18', 'room':'Bedroom 3',  'name':'Water Geyser',    'icon':'bi-droplet-fill',    'type':'blynk'},
    
    # Kitchen
    'kitch_light': {'pin':'V19', 'room':'Kitchen',    'name':'Kitchen Light',   'icon':'bi-lightbulb',       'type':'blynk'},
    'kitch_fan':   {'pin':'V20', 'room':'Kitchen',    'name':'Kitchen Fan',     'icon':'bi-wind',            'type':'blynk'},
    'exhaust':     {'pin':'V21', 'room':'Kitchen',    'name':'Exhaust Fan',     'icon':'bi-fan',             'type':'blynk'},
    'microwave':   {'pin':'V22', 'room':'Kitchen',    'name':'Microwave',       'icon':'bi-box',             'type':'blynk'},
    'fridge':      {'pin':'V23', 'room':'Kitchen',    'name':'Refrigerator',    'icon':'bi-box2',            'type':'blynk'},
}

ROOMS = ['Main Room', 'Bedroom 1', 'Bedroom 2', 'Bedroom 3', 'Kitchen']

# ─── GPIO INITIALIZATION ──────────────────────────────────────────────────────
def init_gpio():
    """Initialize GPIO pins for relays using Active-Low logic"""
    if not GPIO_AVAILABLE:
        return
    
    for dev_id, dev in DEVICES.items():
        if dev.get('type') == 'gpio':
            pin = dev['pin']
            try:
                # initial=GPIO.HIGH ensures relays stay OFF when the Pi boots
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
                print(f"[GPIO] Initialized pin {pin} ({dev['name']}) - OFF (HIGH)")
            except Exception as e:
                print(f"[GPIO Init Error] Pin {pin}: {e}")

# ─── GPIO CONTROL FUNCTIONS ───────────────────────────────────────────────────
class GPIOController:
    """Advanced GPIO controller using Active-Low logic for Relays"""
    
    def __init__(self):
        self._states = {}  # Track GPIO states
        self._blink_threads = {}  # Track active blink threads
        self._lock = threading.Lock()
        
    def set_pin(self, pin, state):
        """Set GPIO pin state with Active-Low logic (ON = LOW, OFF = HIGH)"""
        if not GPIO_AVAILABLE:
            return False
        
        try:
            with self._lock:
                if pin in self._blink_threads:
                    self._blink_threads[pin]['stop'] = True
                    time.sleep(0.1)
                
                # Active-Low Logic: True (ON) -> GPIO.LOW
                GPIO.output(pin, GPIO.LOW if state else GPIO.HIGH)
                self._states[pin] = state
                return True
        except Exception as e:
            print(f"[GPIO Error] Pin {pin}: {e}")
            return False
    
    def get_pin(self, pin):
        """Get current GPIO hardware pin state"""
        if not GPIO_AVAILABLE:
            return False
        try:
            return GPIO.input(pin) == GPIO.LOW
        except Exception:
            return self._states.get(pin, False)
    
    def safety_shutdown_relays(self):
        """Emergency shutdown of all GPIO relays"""
        if not GPIO_AVAILABLE:
            return
        
        print("[GPIO] SAFETY SHUTDOWN - Turning off all relays")
        with self._lock:
            for pin in list(self._blink_threads.keys()):
                self._blink_threads[pin]['stop'] = True
            
            for dev_id, dev in DEVICES.items():
                if dev.get('type') == 'gpio':
                    try:
                        GPIO.output(dev['pin'], GPIO.HIGH) # OFF state
                        self._states[dev['pin']] = False
                    except Exception:
                        pass

gpio_ctrl = GPIOController()

# ─── SPEED OPTIMIZATION 1: Persistent HTTP Session ───────────────────────────
_http = req_lib.Session()
_http.params = {'token': BLYNK_TOKEN}

# ─── SPEED OPTIMIZATION 2: Enhanced Device State Cache with GPIO ─────────────
class DeviceCache:
    def __init__(self):
        self._states  = {k: False for k in DEVICES}
        self._lock    = threading.Lock()
        self._last_refresh = 0
        self.CACHE_TTL = 5

    def get_all(self):
        """Return full state dict including hardware GPIO states"""
        with self._lock:
            states = dict(self._states)
            for dev_id, dev in DEVICES.items():
                if dev.get('type') == 'gpio':
                    states[dev_id] = gpio_ctrl.get_pin(dev['pin'])
            return states

    def get(self, device_key):
        dev = DEVICES.get(device_key)
        if dev and dev.get('type') == 'gpio':
            return gpio_ctrl.get_pin(dev['pin'])
        with self._lock:
            return self._states.get(device_key, False)

    def set(self, device_key, state: bool):
        dev = DEVICES.get(device_key)
        if dev and dev.get('type') == 'gpio':
            gpio_ctrl.set_pin(dev['pin'], state)
        with self._lock:
            self._states[device_key] = state

    def refresh_all(self):
        def _fetch_one(item):
            key, dev = item
            if dev.get('type') == 'gpio':
                return key, gpio_ctrl.get_pin(dev['pin'])
            try:
                r = _http.get(f"{BLYNK_BASE}/get", params={'pin': dev['pin']}, timeout=3)
                return key, (r.status_code == 200 and r.json()[0] == '1')
            except:
                return key, False

        blynk_devices = [(k, v) for k, v in DEVICES.items() if v.get('type') != 'gpio']
        with ThreadPoolExecutor(max_workers=24) as ex:
            futures = {ex.submit(_fetch_one, item): item for item in blynk_devices}
            results = {}
            for f in as_completed(futures, timeout=5):
                try:
                    k, v = f.result()
                    results[k] = v
                except:
                    pass

        with self._lock:
            self._states.update(results)
            self._last_refresh = time.time()

    def start_background_refresh(self):
        def _loop():
            while True:
                try:
                    self.refresh_all()
                except:
                    pass
                time.sleep(self.CACHE_TTL)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        print("[Cache] Background refresh started (every 5s)")

cache = DeviceCache()

# ─── SPEED OPTIMIZATION 3: Non-blocking logs ──────────────────────────────────
_log_executor = ThreadPoolExecutor(max_workers=2)

# ─── BLYNK HELPERS ────────────────────────────────────────────────────────────
def blynk_get(pin):
    try:
        r = _http.get(f"{BLYNK_BASE}/get", params={'pin': pin}, timeout=3)
        return r.status_code == 200 and r.json()[0] == '1'
    except:
        return False

def blynk_set(pin, val):
    try:
        r = _http.get(f"{BLYNK_BASE}/update", params={'token': BLYNK_TOKEN, pin: val}, timeout=3)
        return r.status_code == 200
    except:
        return False

def get_room_devices(room_name):
    states = cache.get_all()
    return {k: {**v, 'state': states.get(k, False)} for k, v in DEVICES.items() if v['room'] == room_name}

def get_all_devices_with_state():
    states = cache.get_all()
    return {k: {**v, 'state': states.get(k, False)} for k, v in DEVICES.items()}

# ─── AUTH & HELPERS ───────────────────────────────────────────────────────────
def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('home.login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('home.login'))
        return f(*args, **kwargs)
    return decorated

def log_action(action):
    if 'user' not in session:
        return
    username   = session['user']['username']
    ip_address = request.remote_addr

    def _write():
        try:
            db.collection('logs').add({
                'username':   username,
                'action':     action,
                'ip_address': ip_address,
                'timestamp':  datetime.now()
            })
        except Exception as e:
            print(f"[Log Error] {e}")

    _log_executor.submit(_write)

def _fb_get_count(collection):
    return len(db.collection(collection).get())

def _fb_get_logs_today():
    today_start = datetime.combine(date.today(), datetime.min.time())
    return len(db.collection('logs').where(filter=FieldFilter('timestamp', '>=', today_start)).get())

def _fb_get_recent_logs():
    return [doc.to_dict() for doc in db.collection('logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).get()]

# ─── HOME BLUEPRINT ───────────────────────────────────────────────────────────
home = Blueprint('home', __name__)

@home.route('/', methods=['GET', 'POST'])
@home.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('admin.dashboard') if session['user']['role'] == 'admin' else url_for('user.dashboard'))
    if request.method == 'POST':
        u  = request.form.get('username', '').strip()
        hp = hash_pw(request.form.get('password', ''))

        adm = db.collection('admin').where(filter=FieldFilter('username', '==', u)).where(filter=FieldFilter('password', '==', hp)).limit(1).get()
        if adm:
            res = adm[0].to_dict()
            session['user'] = {'id': adm[0].id, 'username': u, 'role': 'admin', 'name': res.get('full_name', u)}
            log_action('Login')
            return redirect(url_for('admin.dashboard'))

        usr = db.collection('users').where(filter=FieldFilter('username', '==', u)).where(filter=FieldFilter('password', '==', hp)).limit(1).get()
        if usr:
            res = usr[0].to_dict()
            session['user'] = {'id': usr[0].id, 'username': u, 'role': 'user', 'name': res.get('full_name', u)}
            log_action('Login')
            return redirect(url_for('user.dashboard'))

        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@home.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fn = request.form.get('full_name', '').strip()
        un = request.form.get('username', '').strip()
        em = request.form.get('email', '').strip()
        ph = request.form.get('phone', '').strip()
        pw = request.form.get('password', '')
        cp = request.form.get('confirm_password', '')

        if pw != cp:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('home.signup'))

        if (db.collection('users').where(filter=FieldFilter('username','==',un)).limit(1).get() or
            db.collection('users').where(filter=FieldFilter('email','==',em)).limit(1).get()):
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('home.signup'))

        db.collection('users').add({'full_name': fn, 'username': un, 'email': em, 'phone': ph, 'password': hash_pw(pw), 'created_at': datetime.now()})
        flash('Account created! Please login.', 'success')
        return redirect(url_for('home.login'))
    return render_template('signup.html')

@home.route('/logout')
def logout():
    log_action('Logout')
    session.clear()
    return redirect(url_for('home.login'))

@home.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        found = db.collection('users').where(filter=FieldFilter('email','==',email)).limit(1).get()
        flash('Password reset instructions sent.' if found else 'Email not found.', 'success' if found else 'danger')
    return render_template('forgot_password.html')

@home.route('/contact', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        db.collection('contact_us').add({'username': request.form.get('name', ''), 'email': request.form.get('email', ''), 'subject': request.form.get('subject', ''), 'message': request.form.get('message', ''), 'timestamp': datetime.now()})
        flash('Message sent successfully!', 'success')
    return render_template('contact_us.html')

# ─── USER BLUEPRINT ───────────────────────────────────────────────────────────
user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    states    = cache.get_all()
    on_count  = sum(1 for v in states.values() if v)
    return render_template('users/dashboard.html', user=session['user'], rooms=ROOMS, on_count=on_count, total=len(DEVICES))

@user_bp.route('/main-room')
@login_required
def main_room():
    return render_template('users/room.html', user=session['user'], devices=get_room_devices('Main Room'), room_name='Main Room', room_icon='bi-tv', room_slug='main_room')

@user_bp.route('/bedroom-1')
@login_required
def bedroom_1():
    return render_template('users/room.html', user=session['user'], devices=get_room_devices('Bedroom 1'), room_name='Bedroom 1', room_icon='bi-moon', room_slug='bedroom_1')

@user_bp.route('/bedroom-2')
@login_required
def bedroom_2():
    return render_template('users/room.html', user=session['user'], devices=get_room_devices('Bedroom 2'), room_name='Bedroom 2', room_icon='bi-moon', room_slug='bedroom_2')

@user_bp.route('/bedroom-3')
@login_required
def bedroom_3():
    return render_template('users/room.html', user=session['user'], devices=get_room_devices('Bedroom 3'), room_name='Bedroom 3', room_icon='bi-moon', room_slug='bedroom_3')

@user_bp.route('/kitchen')
@login_required
def kitchen():
    return render_template('users/room.html', user=session['user'], devices=get_room_devices('Kitchen'), room_name='Kitchen', room_icon='bi-cup-hot', room_slug='kitchen')

@user_bp.route('/main-switch')
@login_required
def main_switch():
    states = cache.get_all()
    rooms_status = {room: any(states.get(k, False) for k, v in DEVICES.items() if v['room'] == room) for room in ROOMS}
    return render_template('users/main_switch.html', user=session['user'], rooms=rooms_status)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    doc_ref = db.collection('users').document(session['user']['id'])
    if request.method == 'POST':
        fn = request.form.get('full_name', '').strip()
        em = request.form.get('email', '').strip()
        ph = request.form.get('phone', '').strip()
        doc_ref.update({'full_name': fn, 'email': em, 'phone': ph})
        session['user']['name'] = fn
        flash('Profile updated successfully!', 'success')
    u = doc_ref.get().to_dict() or {}
    u['id'] = session['user']['id']
    return render_template('users/profile.html', user=session['user'], profile=u)

@user_bp.route('/notifications')
@login_required
def notifications():
    try:
        docs = db.collection('notifications').where(filter=FieldFilter('user_id', '==', session['user']['id'])).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50).get()
        notifs = [d.to_dict() for d in docs]
    except:
        notifs = []
    return render_template('users/notifications.html', user=session['user'], notifications=notifs)

@user_bp.route('/reset-credentials', methods=['GET', 'POST'])
@login_required
def reset_credentials():
    if request.method == 'POST':
        curr    = request.form.get('current_password', '')
        new_pw  = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if new_pw != confirm:
            flash('New passwords do not match.', 'danger')
        else:
            doc_ref   = db.collection('users').document(session['user']['id'])
            user_data = doc_ref.get().to_dict()
            if user_data and user_data.get('password') == hash_pw(curr):
                doc_ref.update({'password': hash_pw(new_pw)})
                flash('Password updated successfully!', 'success')
            else:
                flash('Current password is incorrect.', 'danger')
    return render_template('users/reset_credentials.html', user=session['user'])

@user_bp.route('/search')
@login_required
def search():
    q = request.args.get('query', '').lower().strip()
    results = [{'id': k, **v} for k, v in DEVICES.items() if q in v['name'].lower() or q in v['room'].lower()]
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify([r['name'] for r in results])
    return render_template('users/search_results.html', user=session['user'], query=q, results=results)

@user_bp.route('/api/toggle', methods=['POST'])
@login_required
def toggle():
    data  = request.get_json() or {}
    dev_key = data.get('device')
    dev   = DEVICES.get(dev_key)
    if not dev:
        return jsonify({'ok': False, 'error': 'Unknown device'}), 404
    
    state = data.get('state')
    
    if dev.get('type') == 'gpio':
        ok = gpio_ctrl.set_pin(dev['pin'], state)
    else:
        ok = blynk_set(dev['pin'], 1 if state else 0)
    
    if ok:
        cache.set(dev_key, bool(state))
        log_action(f"{'ON' if state else 'OFF'}: {dev['room']} - {dev['name']}")
    
    return jsonify({'ok': ok})

@user_bp.route('/api/toggle-room', methods=['POST'])
@login_required
def toggle_room():
    data  = request.get_json() or {}
    room  = data.get('room')
    state = data.get('state')
    room_devices = [(k, v) for k, v in DEVICES.items() if v['room'] == room]

    def _set_one(item):
        k, d = item
        if d.get('type') == 'gpio':
            ok = gpio_ctrl.set_pin(d['pin'], state)
        else:
            ok = blynk_set(d['pin'], 1 if state else 0)
        if ok:
            cache.set(k, bool(state))
        return ok

    with ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(_set_one, room_devices))

    log_action(f"{'ON' if state else 'OFF'}: All devices in {room}")
    return jsonify({'ok': True, 'count': len(room_devices)})

@user_bp.route('/api/toggle-all', methods=['POST'])
@login_required
def toggle_all():
    state = (request.get_json() or {}).get('state')
    def _set_one(item):
        k, d = item
        if d.get('type') == 'gpio':
            ok = gpio_ctrl.set_pin(d['pin'], state)
        else:
            ok = blynk_set(d['pin'], 1 if state else 0)
        if ok:
            cache.set(k, bool(state))
        return ok
    with ThreadPoolExecutor(max_workers=24) as ex:
        list(ex.map(_set_one, DEVICES.items()))
    log_action(f"{'ON' if state else 'OFF'}: ALL devices")
    return jsonify({'ok': True})

@user_bp.route('/api/status')
@login_required
def device_status():
    return jsonify(cache.get_all())

# ─── ADMIN BLUEPRINT ──────────────────────────────────────────────────────────
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_users    = ex.submit(_fb_get_count, 'users')
        f_contacts = ex.submit(_fb_get_count, 'contact_us')
        f_logs_td  = ex.submit(_fb_get_logs_today)
        f_rec_logs = ex.submit(_fb_get_recent_logs)
        users_count    = f_users.result()
        contacts_count = f_contacts.result()
        logs_today     = f_logs_td.result()
        recent_logs    = f_rec_logs.result()

    states   = cache.get_all()
    on_count = sum(1 for v in states.values() if v)

    return render_template('admin/dashboard.html', user=session['user'], users_count=users_count, logs_today=logs_today, contacts_count=contacts_count, recent_logs=recent_logs, devices_on=on_count, total_devices=len(DEVICES), rooms=ROOMS)

@admin_bp.route('/users')
@admin_required
def user_management():
    users = [dict(doc.to_dict(), id=doc.id) for doc in db.collection('users').get()]
    return render_template('admin/user_management.html', user=session['user'], users=users)

@admin_bp.route('/users/delete/<uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    db.collection('users').document(uid).delete()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/devices')
@admin_required
def device_management():
    status = get_all_devices_with_state()
    return render_template('admin/device_management.html', user=session['user'], devices=status, rooms=ROOMS)

@admin_bp.route('/logs')
@admin_required
def logs():
    all_logs = [doc.to_dict() for doc in db.collection('logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(500).get()]
    return render_template('admin/logs.html', user=session['user'], logs=all_logs)

@admin_bp.route('/notifications')
@admin_required
def notifications():
    contacts = [doc.to_dict() for doc in db.collection('contact_us').order_by('timestamp', direction=firestore.Query.DESCENDING).get()]
    return render_template('admin/notifications.html', user=session['user'], contact_requests=contacts)

@admin_bp.route('/profile', methods=['GET', 'POST'])
@admin_required
def profile():
    doc_ref = db.collection('admin').document(session['user']['id'])
    if request.method == 'POST':
        fn = request.form.get('full_name', '').strip()
        em = request.form.get('email', '').strip()
        doc_ref.update({'full_name': fn, 'email': em})
        session['user']['name'] = fn
        flash('Profile updated!', 'success')
    a = dict(doc_ref.get().to_dict() or {}, id=session['user']['id'])
    return render_template('admin/profile.html', user=session['user'], admin=a)

@admin_bp.route('/reset-credentials', methods=['GET', 'POST'])
@admin_required
def reset_credentials():
    if request.method == 'POST':
        curr    = request.form.get('current_password', '')
        new_pw  = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if new_pw != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            doc_ref    = db.collection('admin').document(session['user']['id'])
            admin_data = doc_ref.get().to_dict()
            if admin_data and admin_data.get('password') == hash_pw(curr):
                doc_ref.update({'password': hash_pw(new_pw)})
                flash('Password updated!', 'success')
            else:
                flash('Current password incorrect.', 'danger')
    return render_template('admin/reset_credentials.html', user=session['user'])

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        flash('Settings saved successfully.', 'success')
    s_docs = db.collection('settings').get()
    settings_data = {doc.to_dict().get('key_name'): doc.to_dict().get('value') for doc in s_docs if not doc.to_dict().get('_init')}
    return render_template('admin/settings.html', user=session['user'], settings=settings_data)

@admin_bp.route('/reports')
@admin_required
def reports():
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_contacts = ex.submit(lambda: [d.to_dict() for d in db.collection('contact_us').order_by('timestamp', direction=firestore.Query.DESCENDING).get()])
        f_logs     = ex.submit(lambda: [d.to_dict() for d in db.collection('logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(100).get()])
        f_users    = ex.submit(lambda: [dict(d.to_dict(), id=d.id) for d in db.collection('users').get()])
        contacts   = f_contacts.result()
        all_logs   = f_logs.result()
        users      = f_users.result()
    return render_template('admin/reports.html', user=session['user'], contacts=contacts, logs=all_logs, users=users)

@admin_bp.route('/monitoring')
@admin_required
def monitoring():
    return render_template('admin/monitoring.html', user=session['user'])

@admin_bp.route('/privacy')
@admin_required
def privacy():
    return render_template('admin/privacy.html', user=session['user'])

@admin_bp.route('/search')
@admin_required
def search():
    q = request.args.get('query', '').lower().strip()
    all_users = [dict(d.to_dict(), id=d.id) for d in db.collection('users').get() if q in d.to_dict().get('username','').lower() or q in d.to_dict().get('email','').lower()]
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify([u['username'] for u in all_users])
    return render_template('admin/search_results.html', user=session['user'], query=q, users=all_users)

@app.route('/esp/status')
def esp_status():
    return jsonify(cache.get_all())

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

# ─── REGISTER BLUEPRINTS ──────────────────────────────────────────────────────
app.register_blueprint(home)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)

# ─── INITIALIZATION SCRIPT (Runs automatically on startup) ────────────────────
def init_db():
    adm = db.collection('admin').where(filter=FieldFilter('username','==','maulin18203')).limit(1).get()
    if not adm:
        db.collection('admin').add({'full_name': 'Maulin K Patel', 'username': 'maulin18203', 'email': 'admin@brighthaven.com', 'password': hash_pw('admin@123'), 'created_at': datetime.now()})
    usr = db.collection('users').where(filter=FieldFilter('username','==','maulin6952')).limit(1).get()
    if not usr:
        db.collection('users').add({'full_name': 'Maulin K Patel', 'username': 'maulin6952', 'email': 'maulin@example.com', 'phone': '9909618203', 'password': hash_pw('user@123'), 'created_at': datetime.now()})
    for col in ['logs', 'contact_us', 'notifications', 'settings']:
        if not db.collection(col).limit(1).get():
            db.collection(col).add({'_init': True, 'timestamp': datetime.now()})

# This setup code executes right when app.py is loaded, preventing the "channel not set up" error.
print("[System] Starting Database and GPIO Initialization...")
init_db()

if GPIO_AVAILABLE:
    print("[GPIO] Initializing Raspberry Pi GPIO pins (Active Low Logic)...")
    init_gpio()

print("[Cache] Initial Blynk state fetch...")
cache.refresh_all()
cache.start_background_refresh()
print("[Server] BrightHaven Smart Home System Ready.")

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    finally:
        if GPIO_AVAILABLE:
            print("[GPIO] Cleaning up pins...")
            GPIO.cleanup()
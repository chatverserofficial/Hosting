import os
import subprocess
import threading
import time
import shutil
import zipfile
import psutil
import json
import hashlib
import secrets
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'user_files')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
DB_FILE = os.path.join(BASE_DIR, 'servers_db.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')


def extract_7z_archive(archive_path, output_dir):
    """Extract a .7z archive using the system 7z command (Termux-friendly)."""
    seven_zip = shutil.which("7z") or shutil.which("7zz")
    if not seven_zip:
        raise RuntimeError(
            "7z command not found. Install it in Termux with: pkg install p7zip"
        )
    result = subprocess.run(
        [seven_zip, "x", "-y", archive_path, f"-o{output_dir}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or "7z extraction failed")


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_ICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='%2300ff00'%3E%3Cpath d='M20 9V7c0-1.1-.9-2-2-2h-4c0-1.1-.9-2-2-2H6c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-2h-2v2H6V5h4v2h8v2h2z'/%3E%3C/svg%3E"

DEFAULT_CONFIG = {
    "site_title": "MY PERSONAL VPS",
    "site_header": "MY PERSONAL VPS",
    "icon_url": DEFAULT_ICON,
    "theme": "matrix",
    "font_family": "default",
    "colors": {
        "matrix": {"name": "Matrix Green", "primary": "#00ff00", "secondary": "#00cc00", "accent": "#00ff80",
                    "background": "#000000", "card_bg": "#0a0a0a", "text": "#00ff00", "danger": "#ff0000",
                    "header_text": "#00ff00", "stats_text": "#00ff00"},
        "night": {"name": "Night Blue", "primary": "#4d88ff", "secondary": "#3366cc", "accent": "#aa88ff",
                   "background": "#000000", "card_bg": "#0a0a0a", "text": "#4d88ff", "danger": "#ff4d4d",
                   "header_text": "#4d88ff", "stats_text": "#4d88ff"},
        "ocean": {"name": "Ocean Blue", "primary": "#3399ff", "secondary": "#0066cc", "accent": "#ff99cc",
                   "background": "#000000", "card_bg": "#0a0a0a", "text": "#3399ff", "danger": "#ff4d4d",
                   "header_text": "#3399ff", "stats_text": "#3399ff"},
        "sunset": {"name": "Sunset Orange", "primary": "#ff9933", "secondary": "#cc6600", "accent": "#ff66b3",
                    "background": "#000000", "card_bg": "#0a0a0a", "text": "#ff9933", "danger": "#ff4d4d",
                    "header_text": "#ff9933", "stats_text": "#ff9933"},
        "blood": {"name": "Blood Red", "primary": "#ff4d4d", "secondary": "#cc0000", "accent": "#ff80bf",
                   "background": "#000000", "card_bg": "#0a0a0a", "text": "#ff4d4d", "danger": "#ff0000",
                   "header_text": "#ff4d4d", "stats_text": "#ff4d4d"},
        "neon": {"name": "Neon Purple", "primary": "#ff66ff", "secondary": "#cc33cc", "accent": "#ffff80",
                  "background": "#000000", "card_bg": "#0a0a0a", "text": "#ff66ff", "danger": "#ff4d4d",
                  "header_text": "#ff66ff", "stats_text": "#ff66ff"},
        "cyber": {"name": "Cyber Cyan", "primary": "#33ffff", "secondary": "#00cccc", "accent": "#ff80ff",
                   "background": "#000000", "card_bg": "#0a0a0a", "text": "#33ffff", "danger": "#ff4d4d",
                   "header_text": "#33ffff", "stats_text": "#33ffff"},
        "vapor": {"name": "Vapor Pink", "primary": "#ff99ff", "secondary": "#cc66cc", "accent": "#80ffff",
                   "background": "#000000", "card_bg": "#0a0a0a", "text": "#ff99ff", "danger": "#ff4d4d",
                   "header_text": "#ff99ff", "stats_text": "#ff99ff"},
        "gold": {"name": "Royal Gold", "primary": "#ffcc66", "secondary": "#cc9933", "accent": "#ffb380",
                  "background": "#000000", "card_bg": "#0a0a0a", "text": "#ffcc66", "danger": "#ff4d4d",
                  "header_text": "#ffcc66", "stats_text": "#ffcc66"},
        "silver": {"name": "Silver Grey", "primary": "#b3b3b3", "secondary": "#808080", "accent": "#cccccc",
                    "background": "#000000", "card_bg": "#0a0a0a", "text": "#b3b3b3", "danger": "#ff4d4d",
                    "header_text": "#b3b3b3", "stats_text": "#b3b3b3"}
    },
    "fonts": {
        "default": "'Segoe UI', sans-serif",
        "hacker": "'Courier New', monospace",
        "terminal": "'Consolas', monospace",
        "code": "'Fira Code', monospace",
        "retro": "'VT323', monospace"
    },
    "background": {
        "type": "blackhole", "url": "", "opacity": 0.82, "speed": 1.0,
        "emoji": "❤️✨💎🔥⭐", "rain_count": 28
    },
    "branding": {"credit": "PERSONAL VPS", "version": "1.0.0"}
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                if 'background' not in config:
                    config['background'] = DEFAULT_CONFIG['background'].copy()
                else:
                    for k, v in DEFAULT_CONFIG['background'].items():
                        config['background'].setdefault(k, v)
                config.setdefault('branding', DEFAULT_CONFIG['branding'].copy())
                config.setdefault('colors', DEFAULT_CONFIG['colors'])
                config.setdefault('font_family', 'default')
                config.setdefault('fonts', DEFAULT_CONFIG['fonts'])
                config.setdefault('theme', 'matrix')
                if not config.get('icon_url'):
                    config['icon_url'] = DEFAULT_ICON
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        if os.path.exists(CONFIG_FILE):
            backup_dir = os.path.join(BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            stamp = time.strftime('%Y%m%d_%H%M%S')
            shutil.copy2(CONFIG_FILE, os.path.join(backup_dir, f'config_{stamp}.json'))
            backups = sorted(
                [os.path.join(backup_dir, x) for x in os.listdir(backup_dir)
                 if x.startswith('config_') and x.endswith('.json')],
                key=os.path.getmtime, reverse=True
            )
            for old_backup in backups[10:]:
                try:
                    os.remove(old_backup)
                except OSError:
                    pass
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")


CONFIG = load_config()
SERVERS = {}


def save_servers():
    try:
        data = {}
        for sid, s in SERVERS.items():
            data[sid] = {
                'cmd': s.get('cmd', ''), 'cwd': s.get('cwd', ''), 'path': s.get('path', ''),
                'auto_restart': s.get('auto_restart', False),
                'restart_interval': s.get('restart_interval', '1h'),
                'status': s.get('status', 'stopped'),
                'last_start_time': s.get('last_start_time', 0)
            }
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving servers: {e}")


def load_servers():
    global SERVERS
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                saved = json.load(f)
                for sid, s in saved.items():
                    SERVERS[sid] = {
                        'process': None, 'cmd': s.get('cmd', ''), 'cwd': s.get('cwd', ''),
                        'auto_restart': s.get('auto_restart', False),
                        'restart_interval': s.get('restart_interval', '1h'),
                        'logs': ["Restored from previous session..."],
                        'status': s.get('status', 'stopped'), 'path': s.get('path', ''),
                        'last_start_time': s.get('last_start_time', 0)
                    }
        except Exception as e:
            print(f"Error loading servers: {e}")


load_servers()


@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_file(os.path.join(STATIC_FOLDER, filename))
    except Exception:
        return "File not found", 404


def get_system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
    except Exception:
        cpu, ram, disk = 0, 0, 0
    return cpu, ram, disk


def log_monitor(server_id, proc_obj):
    server = SERVERS.get(server_id)
    if not server:
        return
    try:
        for line in iter(proc_obj.stdout.readline, ''):
            if server_id not in SERVERS or SERVERS[server_id].get('process') != proc_obj:
                break
            if line:
                cleaned_line = line.strip()
                if cleaned_line:
                    if len(SERVERS[server_id]['logs']) > 1000:
                        SERVERS[server_id]['logs'] = SERVERS[server_id]['logs'][-900:]
                    SERVERS[server_id]['logs'].append(cleaned_line)
    except Exception as e:
        print(f"Log monitor error: {e}")
    finally:
        try:
            proc_obj.stdout.close()
        except Exception:
            pass

    if server_id in SERVERS and SERVERS[server_id].get('process') == proc_obj:
        SERVERS[server_id]['status'] = 'stopped'
        SERVERS[server_id]['process'] = None
        SERVERS[server_id]['logs'].append(">>> Process terminated.")
        save_servers()


def kill_process_completely(proc):
    try:
        if proc is None:
            return
        parent = psutil.Process(proc.pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except Exception:
                pass
        gone, alive = psutil.wait_procs(children, timeout=3)
        for child in alive:
            try:
                child.kill()
            except Exception:
                pass
        try:
            parent.terminate()
            parent.wait(timeout=3)
        except Exception:
            try:
                parent.kill()
            except Exception:
                pass
    except Exception as e:
        print(f"Error killing process: {e}")


def run_install_command(server_id, command):
    if server_id in SERVERS:
        SERVERS[server_id]['logs'].append(f">>> {command}")
        try:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            for line in iter(process.stdout.readline, ''):
                if line:
                    SERVERS[server_id]['logs'].append(line.strip())
                    if len(SERVERS[server_id]['logs']) > 1000:
                        SERVERS[server_id]['logs'] = SERVERS[server_id]['logs'][-900:]
            SERVERS[server_id]['logs'].append(">>> Installation finished.")
        except Exception as e:
            SERVERS[server_id]['logs'].append(f"Error: {str(e)}")


def start_server_internal(server_id, server):
    if server['status'] == 'running':
        return True

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    work_dir = os.path.join(server['path'], server.get('cwd', ''))
    if not os.path.exists(work_dir):
        work_dir = server['path']

    try:
        if not server['cmd'] or server['cmd'].strip() == '':
            server['logs'].append(">>> Error: No start command specified")
            return False
        if not os.path.exists(work_dir):
            server['logs'].append(f">>> Error: Working directory does not exist: {work_dir}")
            return False

        proc = subprocess.Popen(
            server['cmd'], shell=True, cwd=work_dir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            text=True, bufsize=1, universal_newlines=True, env=env,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        server['process'] = proc
        server['status'] = 'running'
        server['last_start_time'] = time.time()
        server['logs'].append(f">>> Server started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        threading.Thread(target=log_monitor, args=(server_id, proc), daemon=True).start()
        save_servers()
        return True
    except Exception as e:
        server['logs'].append(f">>> Failed to start: {str(e)}")
        return False


def auto_restarter():
    while True:
        time.sleep(5)
        current_time = time.time()
        for server_id, server in list(SERVERS.items()):
            try:
                if server.get('status') == 'running' and server.get('auto_restart'):
                    interval_str = server.get('restart_interval', '1h')
                    interval_map = {
                        '30s': 30, '1m': 60, '5m': 300, '10m': 600, '30m': 1800,
                        '1h': 3600, '2h': 7200, '3h': 10800, '6h': 21600,
                        '12h': 43200, '24h': 86400
                    }
                    interval_sec = interval_map.get(interval_str, 3600)
                    last_start = server.get('last_start_time', current_time)
                    if current_time - last_start >= interval_sec:
                        server['logs'].append(f">>> Auto-restarting server (Interval: {interval_str})...")
                        if server.get('process'):
                            kill_process_completely(server['process'])
                            server['process'] = None
                        server['status'] = 'stopped'
                        start_server_internal(server_id, server)
            except Exception as e:
                print(f"Error in auto_restarter for {server_id}: {e}")


threading.Thread(target=auto_restarter, daemon=True).start()


# --- MAIN ROUTES (no login/session required) ---
@app.route('/')
def index():
    try:
        cpu, ram, disk = get_system_stats()
        current_colors = CONFIG['colors'].get(CONFIG['theme'], CONFIG['colors']['matrix'])
        serializable_servers = {}
        for sid, s in SERVERS.items():
            serializable_servers[sid] = {
                'cmd': s.get('cmd', ''), 'cwd': s.get('cwd', ''),
                'auto_restart': s.get('auto_restart', False),
                'restart_interval': s.get('restart_interval', '1h'),
                'status': s.get('status', 'stopped'), 'path': s.get('path', ''),
                'last_start_time': s.get('last_start_time', 0)
            }
        return render_template(
            'index.html', servers=serializable_servers, cpu=cpu, ram=ram, disk=disk,
            total_count=len(SERVERS),
            running_count=sum(1 for s in SERVERS.values() if s['status'] == 'running'),
            config=CONFIG, colors=current_colors
        )
    except Exception as e:
        print(f"Index error: {e}")
        return f"Error: {e}", 500


@app.route('/create_server', methods=['POST'])
def create_server():
    try:
        server_name = request.form.get('server_name').strip().replace(" ", "_")
        start_command = request.form.get('start_command').strip()
        if not server_name:
            return "Server name required", 400
        if server_name in SERVERS:
            return "Server name already exists", 400

        file = request.files.get('file')
        server_path = os.path.join(UPLOAD_FOLDER, server_name)
        os.makedirs(server_path, exist_ok=True)

        if file and file.filename:
            file_path = os.path.join(server_path, file.filename)
            file.save(file_path)
            if file.filename.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(server_path)
                except Exception as e:
                    print(f"Zip extraction error: {e}")
            elif file.filename.lower().endswith('.7z'):
                try:
                    extract_7z_archive(file_path, server_path)
                except Exception as e:
                    print(f"7z extraction error: {e}")

        SERVERS[server_name] = {
            'process': None, 'cmd': start_command, 'cwd': '',
            'logs': [f">>> Server '{server_name}' created at {time.strftime('%Y-%m-%d %H:%M:%S')}"],
            'auto_restart': False, 'restart_interval': '1h', 'last_start_time': 0,
            'status': 'stopped', 'path': server_path
        }
        save_servers()
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Create server error: {e}")
        return f"Error: {e}", 500


@app.route('/action/<server_id>/<action>')
def server_action(server_id, action):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        server = SERVERS[server_id]

        if action == 'start':
            start_server_internal(server_id, server)
            return redirect(url_for('index'))
        elif action == 'stop':
            if server['process']:
                kill_process_completely(server['process'])
                server['process'] = None
            server['status'] = 'stopped'
            server['logs'].append(f">>> Stopped by user at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            save_servers()
            return redirect(url_for('index'))
        elif action == 'restart':
            if server['process']:
                kill_process_completely(server['process'])
                server['process'] = None
            server['status'] = 'stopped'
            server['logs'].append(">>> Manual restart triggered...")
            time.sleep(1)
            start_server_internal(server_id, server)
            return redirect(url_for('index'))
        elif action == 'delete':
            if server['process']:
                kill_process_completely(server['process'])
                server['process'] = None
            if os.path.exists(server['path']):
                shutil.rmtree(server['path'], ignore_errors=True)
            del SERVERS[server_id]
            save_servers()
            return redirect(url_for('index'))
        else:
            return jsonify({'error': 'Invalid action'}), 400
    except Exception as e:
        print(f"Server action error: {e}")
        if server_id in SERVERS:
            SERVERS[server_id]['logs'].append(f"Error during {action}: {str(e)}")
        return redirect(url_for('index'))


@app.route('/rename_file/<server_id>', methods=['POST'])
def rename_file(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        old_name = request.form.get('old_name')
        new_name = request.form.get('new_name')
        subpath = request.form.get('path', '')
        if not old_name or not new_name:
            return jsonify({'error': 'Missing names'}), 400
        subpath = subpath.replace('..', '')
        old_name = old_name.replace('..', '')
        new_name = new_name.replace('..', '')
        base_path = SERVERS[server_id]['path']
        old_path = os.path.join(base_path, subpath, old_name)
        new_path = os.path.join(base_path, subpath, new_name)
        if not os.path.realpath(old_path).startswith(os.path.realpath(base_path)):
            return jsonify({'error': 'Invalid path'}), 400
        if not os.path.exists(old_path):
            return jsonify({'error': 'File not found'}), 404
        if os.path.exists(new_path):
            return jsonify({'error': 'Destination already exists'}), 400
        os.rename(old_path, new_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/file_content/<server_id>')
def file_content(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        filename = request.args.get('filename')
        subpath = request.args.get('path', '')
        if not filename:
            return jsonify({'error': 'No filename'}), 400
        subpath = subpath.replace('..', '')
        filename = filename.replace('..', '')
        file_path = os.path.join(SERVERS[server_id]['path'], subpath, filename)
        if not os.path.realpath(file_path).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        if not os.path.isfile(file_path):
            return jsonify({'error': 'File not found'}), 404
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/save_file/<server_id>', methods=['POST'])
def save_file(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        filename = request.form.get('filename')
        subpath = request.form.get('path', '')
        content = request.form.get('content')
        if not filename or content is None:
            return jsonify({'error': 'Missing data'}), 400
        subpath = subpath.replace('..', '')
        filename = filename.replace('..', '')
        file_path = os.path.join(SERVERS[server_id]['path'], subpath, filename)
        if not os.path.realpath(file_path).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/create_file/<server_id>', methods=['POST'])
def create_file(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        filename = request.form.get('filename')
        subpath = request.form.get('path', '')
        content = request.form.get('content', '')
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        subpath = subpath.replace('..', '')
        filename = filename.replace('..', '')
        file_path = os.path.join(SERVERS[server_id]['path'], subpath, filename)
        if not os.path.realpath(file_path).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        if os.path.exists(file_path):
            return jsonify({'error': 'File already exists'}), 400
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/extract_archive/<server_id>/<filename>', methods=['POST'])
def extract_archive(server_id, filename):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        subpath = request.form.get('path', '')
        subpath = subpath.replace('..', '')
        filename = filename.replace('..', '')
        archive_path = os.path.join(SERVERS[server_id]['path'], subpath, filename)
        if not os.path.realpath(archive_path).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        if not os.path.exists(archive_path):
            return jsonify({'error': 'Archive not found'}), 404
        extract_to = os.path.dirname(archive_path)
        if filename.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as z:
                z.extractall(extract_to)
        elif filename.lower().endswith('.7z'):
            extract_7z_archive(archive_path, extract_to)
        else:
            return jsonify({'error': 'Unsupported archive format'}), 400
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_logs/<server_id>')
def get_logs(server_id):
    try:
        if server_id in SERVERS:
            return jsonify({'logs': "\n".join(SERVERS[server_id]['logs'][-500:])})
        return jsonify({'logs': ''})
    except Exception as e:
        return jsonify({'logs': f'Error: {e}'})


@app.route('/send_input/<server_id>', methods=['POST'])
def send_input(server_id):
    """Terminal/console input -> forwarded to the running process's stdin."""
    try:
        cmd = request.form.get('command')
        if not cmd:
            return jsonify({'status': 'error', 'message': 'No command provided'})
        if server_id not in SERVERS:
            return jsonify({'status': 'error', 'message': 'Server not found'})
        server = SERVERS[server_id]
        if not server['process']:
            return jsonify({'status': 'error', 'message': 'Process not running'})
        proc = server['process']
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()
            server['logs'].append(f">>> Input: {cmd}")
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'status': 'error', 'message': 'stdin closed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/files/<server_id>')
def list_files(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        subpath = request.args.get('path', '')
        if '..' in subpath:
            subpath = ''
        base_path = SERVERS[server_id]['path']
        full_path = os.path.join(base_path, subpath)
        if not os.path.realpath(full_path).startswith(os.path.realpath(base_path)):
            full_path = base_path
            subpath = ''
        if not os.path.exists(full_path):
            full_path = base_path
            subpath = ''

        files = []
        total_size = 0
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            is_file = os.path.isfile(item_path)
            size = 0
            if is_file:
                size = os.path.getsize(item_path)
                total_size += size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            files.append({
                'name': item, 'size': size_str, 'raw_size': size,
                'type': 'file' if is_file else 'dir',
                'ext': os.path.splitext(item)[1].lower() if is_file else ''
            })

        if total_size < 1024:
            total_size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            total_size_str = f"{total_size/1024:.1f} KB"
        else:
            total_size_str = f"{total_size/(1024*1024):.1f} MB"

        files.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))

        return jsonify({
            'files': files, 'cmd': SERVERS[server_id]['cmd'],
            'cwd': SERVERS[server_id].get('cwd', ''),
            'auto_restart': SERVERS[server_id].get('auto_restart', False),
            'restart_interval': SERVERS[server_id].get('restart_interval', '1h'),
            'current_path': subpath, 'total_size': total_size_str
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload/<server_id>', methods=['POST'])
def upload_file(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        file = request.files.get('file')
        subpath = request.form.get('path', '')
        if '..' in subpath:
            subpath = ''
        if not file or not file.filename:
            return jsonify({'error': 'No file provided'}), 400
        target_dir = os.path.join(SERVERS[server_id]['path'], subpath)
        if not os.path.realpath(target_dir).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, file.filename)
        file.save(file_path)

        if file.filename.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(file_path, 'r') as z:
                    z.extractall(target_dir)
                return jsonify({'status': 'ok', 'message': 'File uploaded and extracted successfully'})
            except Exception as e:
                return jsonify({'status': 'ok', 'warning': f'File uploaded but extraction failed: {str(e)}'})
        elif file.filename.lower().endswith('.7z'):
            try:
                extract_7z_archive(file_path, target_dir)
                return jsonify({'status': 'ok', 'message': 'File uploaded and extracted successfully'})
            except Exception as e:
                return jsonify({'status': 'ok', 'warning': f'File uploaded but extraction failed: {str(e)}'})

        return jsonify({'status': 'ok', 'message': 'File uploaded successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/create_folder/<server_id>', methods=['POST'])
def create_folder(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        folder_name = request.form.get('name')
        subpath = request.form.get('path', '')
        if '..' in subpath:
            subpath = ''
        if not folder_name:
            return jsonify({'error': 'Folder name required'}), 400
        folder_name = folder_name.replace('..', '')
        target = os.path.join(SERVERS[server_id]['path'], subpath, folder_name)
        if not os.path.realpath(target).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        os.makedirs(target, exist_ok=True)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<server_id>/<filename>')
def download_file(server_id, filename):
    try:
        if server_id not in SERVERS:
            return "Server not found", 404
        subpath = request.args.get('path', '')
        if '..' in subpath or '..' in filename:
            return "Invalid path", 400
        file_path = os.path.join(SERVERS[server_id]['path'], subpath, filename)
        if not os.path.realpath(file_path).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return "Invalid path", 400
        if not os.path.exists(file_path):
            return "File not found", 404
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return str(e), 500


@app.route('/delete_file/<server_id>/<filename>')
def delete_file(server_id, filename):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        subpath = request.args.get('path', '')
        if '..' in subpath or '..' in filename:
            return jsonify({'error': 'Invalid path'}), 400
        file_path = os.path.join(SERVERS[server_id]['path'], subpath, filename)
        if not os.path.realpath(file_path).startswith(os.path.realpath(SERVERS[server_id]['path'])):
            return jsonify({'error': 'Invalid path'}), 400
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/update_settings/<server_id>', methods=['POST'])
def update_settings(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        cmd = request.form.get('cmd', '').strip()
        cwd = request.form.get('cwd', '').strip()
        auto_restart = request.form.get('auto_restart') == 'true'
        restart_interval = request.form.get('restart_interval', '1h')
        SERVERS[server_id]['cmd'] = cmd
        SERVERS[server_id]['cwd'] = cwd
        SERVERS[server_id]['auto_restart'] = auto_restart
        SERVERS[server_id]['restart_interval'] = restart_interval
        SERVERS[server_id]['logs'].append(f">>> Settings updated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        save_servers()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- PACKAGE MANAGEMENT ---
@app.route('/install_pkg/<server_id>', methods=['POST'])
def install_pkg(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        pkg_type = request.form.get('type')
        pkg_name = request.form.get('name')
        if not pkg_name:
            return jsonify({'error': 'Package name required'}), 400
        cmd = ""
        if pkg_type == 'pip':
            cmd = f"pip install {pkg_name}"
        elif pkg_type == 'pkg':
            cmd = f"pkg install -y {pkg_name}"
        elif pkg_type == 'apt':
            cmd = f"apt-get install -y {pkg_name}"
        elif pkg_type == 'npm':
            cmd = f"npm install -g {pkg_name}"
        else:
            return jsonify({'error': 'Invalid package type'}), 400
        threading.Thread(target=run_install_command, args=(server_id, cmd), daemon=True).start()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/uninstall_pkg/<server_id>', methods=['POST'])
def uninstall_pkg(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Server not found'}), 404
        pkg_type = request.form.get('type')
        pkg_name = request.form.get('name')
        if not pkg_name:
            return jsonify({'error': 'Package name required'}), 400
        cmd = ""
        if pkg_type == 'pip':
            cmd = f"pip uninstall -y {pkg_name}"
        elif pkg_type == 'pkg':
            cmd = f"pkg uninstall -y {pkg_name}"
        elif pkg_type == 'apt':
            cmd = f"apt-get remove -y {pkg_name}"
        elif pkg_type == 'npm':
            cmd = f"npm uninstall -g {pkg_name}"
        else:
            return jsonify({'error': 'Invalid package type'}), 400
        threading.Thread(target=run_install_command, args=(server_id, cmd), daemon=True).start()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- TELEGRAM BOT QUICK DEPLOY (multiple bots supported, one per token) ---
@app.route('/telegram_bot', methods=['POST'])
def telegram_bot():
    try:
        token = request.form.get('token')
        if not token:
            return jsonify({'error': 'Token required'}), 400
        if ':' not in token or len(token) < 40:
            return jsonify({'error': 'Invalid token format'}), 400

        timestamp = int(time.time())
        server_name = f"tg_bot_{timestamp}"
        server_path = os.path.join(UPLOAD_FOLDER, server_name)
        os.makedirs(server_path, exist_ok=True)

        bot_script = '''import asyncio
import requests
import time
import platform
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = "{}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
START_TIME = time.time()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "\U0001F916 *Personal VPS Telegram Bot*\\n\\n"
        "/api <url> - Check API endpoint\\n"
        "/ping - Check bot status\\n"
        "/uptime - Show bot uptime\\n"
        "/info - Show system info",
        parse_mode='Markdown'
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "/start - Welcome message\\n"
        "/help - Show this help\\n"
        "/api <url> - Check API endpoint\\n"
        "/ping - Check bot status\\n"
        "/uptime - Show bot uptime\\n"
        "/info - Show system info",
        parse_mode='Markdown'
    )


@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("Pong! Bot is alive!")


@dp.message(Command("uptime"))
async def uptime(message: types.Message):
    uptime_seconds = int(time.time() - START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    uptime_str = "Uptime: "
    if days > 0:
        uptime_str += f"{{days}}d "
    uptime_str += f"{{hours}}h {{minutes}}m {{seconds}}s"
    await message.answer(uptime_str)


@dp.message(Command("info"))
async def info(message: types.Message):
    info_text = (
        f"Platform: {{platform.system()}} {{platform.release()}}\\n"
        f"Python: {{platform.python_version()}}\\n"
        f"Time: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}"
    )
    await message.answer(info_text)


@dp.message(Command("api"))
async def api_check(message: types.Message):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.answer("Usage: /api <url>")
        return
    url = args[1].strip()
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        r = requests.get(url, timeout=15, headers={{'User-Agent': 'Mozilla/5.0'}})
        try:
            import json as _json
            text = _json.dumps(r.json(), indent=2, ensure_ascii=False)
        except Exception:
            text = r.text
        if len(text) > 3500:
            text = text[:3500] + "\\n\\n... (truncated)"
        await message.answer(f"Status: {{r.status_code}} | Time: {{r.elapsed.total_seconds():.2f}}s\\n```\\n{{text}}\\n```", parse_mode='Markdown')
    except requests.exceptions.Timeout:
        await message.answer("Error: Request timeout")
    except requests.exceptions.ConnectionError:
        await message.answer("Error: Connection failed")
    except Exception as e:
        await message.answer(f"Error: {{str(e)}}")


async def main():
    print("Bot Started Successfully!")
    me = await bot.get_me()
    print(f"Bot Username: @{{me.username}}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
'''.format(token)

        script_path = os.path.join(server_path, "bot.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(bot_script)

        with open(os.path.join(server_path, "requirements.txt"), 'w') as f:
            f.write("aiogram==3.4.1\nrequests==2.31.0")

        readme = f"""# Telegram Bot - {server_name}
Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

Commands: /start /help /api <url> /ping /uptime /info
Start command: pip install -r requirements.txt && python bot.py
"""
        with open(os.path.join(server_path, "README.txt"), 'w') as f:
            f.write(readme)

        SERVERS[server_name] = {
            'process': None,
            'cmd': 'pip install -r requirements.txt && python bot.py',
            'cwd': '',
            'logs': [
                f">>> Telegram Bot created at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f">>> Token: {token[:10]}...{token[-5:]}",
                ">>> Use 'Start' to launch the bot"
            ],
            'auto_restart': True,
            'restart_interval': '24h',
            'last_start_time': 0,
            'status': 'stopped',
            'path': server_path
        }
        save_servers()

        return jsonify({
            'status': 'ok',
            'server_name': server_name,
            'message': 'Bot created successfully! Start it from dashboard.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- THEME & SETTINGS ---
@app.route('/update_config', methods=['POST'])
def update_config():
    try:
        site_title = request.form.get('site_title')
        site_header = request.form.get('site_header')
        icon_url = request.form.get('icon_url')
        theme = request.form.get('theme')
        font_family = request.form.get('font_family')
        if site_title:
            CONFIG['site_title'] = site_title
        if site_header:
            CONFIG['site_header'] = site_header
        if icon_url:
            CONFIG['icon_url'] = icon_url
        if theme and theme in CONFIG['colors']:
            CONFIG['theme'] = theme
        if font_family and font_family in CONFIG['fonts']:
            CONFIG['font_family'] = font_family
        save_config(CONFIG)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


ALLOWED_BG_EXTENSIONS = {'.mp4', '.webm', '.mov', '.jpg', '.jpeg', '.png', '.webp', '.gif'}


@app.route('/upload_background', methods=['POST'])
def upload_background():
    try:
        media = request.files.get('background_file')
        if not media or not media.filename:
            return jsonify({'error': 'No background file selected'}), 400
        ext = os.path.splitext(media.filename)[1].lower()
        if ext not in ALLOWED_BG_EXTENSIONS:
            return jsonify({'error': 'Unsupported background format'}), 400
        bg_dir = os.path.join(STATIC_FOLDER, 'backgrounds')
        os.makedirs(bg_dir, exist_ok=True)
        safe_name = f"bg_{secrets.token_hex(8)}{ext}"
        target = os.path.join(bg_dir, safe_name)
        media.save(target)

        old_url = CONFIG.get('background', {}).get('url', '')
        if old_url.startswith('/static/backgrounds/'):
            old_file = os.path.join(BASE_DIR, old_url.lstrip('/').replace('/', os.sep))
            if os.path.isfile(old_file) and os.path.realpath(old_file).startswith(os.path.realpath(bg_dir)):
                try:
                    os.remove(old_file)
                except OSError:
                    pass

        CONFIG.setdefault('background', {})
        CONFIG['background']['url'] = f'/static/backgrounds/{safe_name}'
        save_config(CONFIG)
        return jsonify({'status': 'ok', 'url': CONFIG['background']['url']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/update_background', methods=['POST'])
def update_background():
    try:
        bg_type = request.form.get('background_type', 'blackhole')
        allowed_types = {'black', 'blackhole', 'emoji', 'rain', 'image', 'video'}
        if bg_type not in allowed_types:
            return jsonify({'error': 'Invalid background type'}), 400
        CONFIG.setdefault('background', {})
        CONFIG['background']['type'] = bg_type
        CONFIG['background']['opacity'] = max(0.05, min(1.0, float(request.form.get('opacity', 0.82))))
        CONFIG['background']['speed'] = max(0.2, min(4.0, float(request.form.get('speed', 1.0))))
        CONFIG['background']['emoji'] = (request.form.get('emoji') or '❤️✨💎🔥⭐')[:200]
        CONFIG['background']['rain_count'] = max(5, min(80, int(request.form.get('rain_count', 28))))
        save_config(CONFIG)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/reset_background', methods=['POST'])
def reset_background():
    try:
        old_url = CONFIG.get('background', {}).get('url', '')
        if old_url.startswith('/static/backgrounds/'):
            old_file = os.path.join(BASE_DIR, old_url.lstrip('/').replace('/', os.sep))
            bg_dir = os.path.join(STATIC_FOLDER, 'backgrounds')
            if os.path.isfile(old_file) and os.path.realpath(old_file).startswith(os.path.realpath(bg_dir)):
                try:
                    os.remove(old_file)
                except OSError:
                    pass
        CONFIG['background'] = DEFAULT_CONFIG['background'].copy()
        save_config(CONFIG)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/change_password', methods=['POST'])
def change_password():
    # No login/auth exists in this build, so this is a harmless no-op kept
    # only so the existing "Settings" UI in index.html doesn't break.
    return jsonify({'status': 'ok', 'message': 'No authentication is enabled on this panel.'})


@app.route('/server_info/<server_id>')
def server_info(server_id):
    try:
        if server_id not in SERVERS:
            return jsonify({'error': 'Not found'}), 404
        s = SERVERS[server_id]
        uptime = 0
        if s['status'] == 'running' and s['last_start_time'] > 0:
            uptime = int(time.time() - s['last_start_time'])
        return jsonify({
            'status': s['status'], 'auto_restart': s.get('auto_restart', False),
            'restart_interval': s.get('restart_interval', '1h'),
            'last_start_time': s.get('last_start_time', 0), 'uptime': uptime
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/system_stats')
def system_stats():
    try:
        cpu, ram, disk = get_system_stats()
        return jsonify({'cpu': cpu, 'ram': ram, 'disk': disk})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/ping")
def ping():
    return "alive"


@app.route("/json")
def json_alive():
    return jsonify({"status": "alive", "time": time.time(), "version": "1.0.0"})


@app.errorhandler(404)
def not_found(e):
    # There's no login page anymore, so any stray /login or /logout link
    # (still present in the old sidebar markup) just lands back on the dashboard.
    return redirect(url_for('index'))


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    port = int(os.environ.get("PORT", 30099))
    debug = os.environ.get("DEBUG", "False").lower() == "true"

    print("=" * 50)
    print("Personal VPS Panel - Starting (no login)...")
    print("=" * 50)
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"Servers file: {DB_FILE}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Static folder: {STATIC_FOLDER}")
    print("=" * 50)
    print("WARNING: no authentication. Bind to 127.0.0.1 or a private")
    print("network only unless you add your own access control.")
    print("=" * 50)

    # Personal/local use only. Change host to "127.0.0.1" to
    # restrict access to this device only.
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)

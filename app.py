import os
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Muhib_AlqadamiCall.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'muhib_secret_2026'
db = SQLAlchemy(app)

if not os.path.exists('uploads'): os.makedirs('uploads')

# جداول البيانات: المستخدمين والرسائل
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context(): db.create_all()

# واجهة المستخدم الاحترافية
HTML_V2 = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Muhib_AlqadamiCall V2</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; background: #e5ddd5; display: flex; height: 100vh; overflow: hidden; }
        .side { width: 30%; background: #ffffff; border-left: 1px solid #ddd; display: flex; flex-direction: column; }
        .chat { width: 70%; display: flex; flex-direction: column; background: #e5ddd5; }
        .header { background: #075e54; color: white; padding: 15px; font-weight: bold; display: flex; justify-content: space-between; }
        .user-list { flex: 1; overflow-y: auto; }
        .user-box { padding: 15px; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; }
        .status { width: 10px; height: 10px; background: #25d366; border-radius: 50%; }
        .msg-area { flex: 1; overflow-y: auto; padding: 20px; }
        .msg-bubble { background: white; padding: 8px 12px; border-radius: 10px; margin-bottom: 8px; width: fit-content; }
        .input-bar { padding: 10px; background: #f0f0f0; display: flex; gap: 10px; }
        input { flex: 1; border-radius: 20px; border: 1px solid #ddd; padding: 10px; outline: none; }
    </style>
</head>
<body>
    <div class="side">
        <div class="header">المتصلون</div>
        <div id="uList" class="user-list"></div>
    </div>
    <div class="chat">
        <div class="header">Muhib_AlqadamiCall <span id="myName"></span></div>
        <div id="mBox" class="msg-area"></div>
        <div class="input-bar">
            <input type="text" id="mInput" placeholder="اكتب رسالة...">
            <button onclick="send()" style="border:none; background:none; color:#075e54; font-size:20px;"><i class="fas fa-paper-plane"></i></button>
        </div>
    </div>
    <script>
        const u = new URLSearchParams(window.location.search).get('u');
        document.getElementById('myName').innerText = "(أنا: " + u + ")";

        function update() {
            fetch('/api/sync?u=' + u).then(r => r.json()).then(data => {
                let uH = '';
                data.users.forEach(user => {
                    uH += `<div class="user-box"><span>${user}</span> 
                           <div style="display:flex; gap:10px;"><i class="fas fa-video" onclick="call('${user}')" style="color:#075e54; cursor:pointer"></i><div class="status"></div></div></div>`;
                });
                document.getElementById('uList').innerHTML = uH;
                
                let mH = '';
                data.msgs.forEach(m => {
                    mH += `<div class="msg-bubble"><b>${m.s}:</b> ${m.c}</div>`;
                });
                document.getElementById('mBox').innerHTML = mH;
            });
        }

        function send() {
            const i = document.getElementById('mInput');
            fetch('/api/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({u: u, c: i.value})
            }).then(() => { i.value = ''; update(); });
        }

        function call(t) {
            alert("طلب اتصال فيديو مع " + t);
            window.open("https://meet.jit.si/MuhibCall_" + t, "_blank");
        }

        setInterval(update, 3000);
        update();
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return '<body style="background:#075e54; color:white; text-align:center; padding-top:100px; font-family:sans-serif;">' \
           '<h2>Muhib_AlqadamiCall</h2>' \
           '<input id="n" placeholder="اسمك" style="padding:10px; border-radius:20px; border:none;"><br><br>' \
           '<button onclick="location.href=\'/main?u=\'+document.getElementById(\'n\').value" style="padding:10px 30px; border-radius:20px; border:none; background:#25d366; color:white; font-weight:bold; cursor:pointer;">دخول</button></body>'

@app.route('/main')
def main():
    u = request.args.get('u')
    if not User.query.filter_by(username=u).first():
        db.session.add(User(username=u))
        db.session.commit()
    return render_template_string(HTML_V2, user=u)

@app.route('/api/sync')
def sync():
    me = request.args.get('u')
    # تحديث حالة المستخدم (متصل)
    curr = User.query.filter_by(username=me).first()
    if curr: curr.last_seen = datetime.utcnow(); db.session.commit()
    
    # جلب المتصلين في آخر دقيقة فقط
    limit = datetime.utcnow() - timedelta(minutes=1)
    users = User.query.filter(User.last_seen > limit).all()
    msgs = Message.query.order_by(Message.timestamp.desc()).limit(20).all()
    
    return jsonify({
        "users": [x.username for x in users if x.username != me],
        "msgs": [{"s": m.sender, "c": m.content} for m in reversed(msgs)]
    })

@app.route('/api/send', methods=['POST'])
def send_api():
    d = request.json
    db.session.add(Message(sender=d['u'], content=d['c']))
    db.session.commit()
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import Flask, request, render_template_string, redirect, make_response
import datetime
import json
import os
import requests
import socket
import csv
from io import StringIO
from threading import Timer
import sys

app = Flask(__name__)

# เก็บข้อมูลใน memory (บน Render ใช้ file-based storage)
logs = []

# ============================================
# CONFIGURATION FOR RENDER
# ============================================

# Render กำหนด port จาก environment variable
PORT = int(os.environ.get('PORT', 5000))
# บน Render ไม่สามารถใช้ 0.0.0.0 ได้บางกรณี
HOST = '0.0.0.0'

# ไฟล์เก็บข้อมูล
DATA_FILE = 'click_logs.json'

# ============================================
# HTML TEMPLATES (ใช้แบบเดิม)
# ============================================

HTML_HOME = '''
<!DOCTYPE html>
<html>
<head>
    <title>🖥️ IP Tracker แสดงที่อยู่ละเอียด</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="ระบบติดตามตำแหน่งโดยประมาณจาก IP Address สำหรับการเรียนรู้">
    <style>
        * { font-family: 'Segoe UI', 'Sukhumvit Set', 'Kanit', sans-serif; }
        body { max-width: 1000px; margin: 0 auto; padding: 20px; background: #f8f9fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.08); margin-bottom: 25px; }
        .link-box { background: #e3f2fd; padding: 20px; border-radius: 10px; border: 2px dashed #2196F3; margin: 15px 0; }
        button { background: #2196F3; color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 5px; transition: 0.3s; }
        button:hover { background: #1976D2; transform: translateY(-2px); }
        input { padding: 10px; border: 1px solid #ddd; border-radius: 5px; width: 70%; }
        .stats { display: flex; justify-content: space-around; text-align: center; margin: 20px 0; }
        .stat-item { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .ip-display { font-family: monospace; font-size: 18px; color: #d32f2f; font-weight: bold; }
        .render-notice { 
            background: #d4edda; 
            border: 1px solid #c3e6cb; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0;
            color: #155724;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌍 IP Tracker แสดงที่อยู่ละเอียด</h1>
        <p>ติดตามตำแหน่งโดยประมาณจาก IP Address</p>
        <p style="font-size: 0.9em; opacity: 0.9;">กำลังทำงานบน Render.com</p>
    </div>
    
    {% if is_render %}
    <div class="render-notice">
        <h3>🚀 ระบบกำลังทำงานบน Render.com</h3>
        <p>✅ ลิงก์นี้สามารถแชร์ให้คนอื่นใช้งานได้ทันที</p>
        <p>🌐 ลิงก์สาธารณะ: <strong>{{ render_url }}</strong></p>
        <p>📱 สามารถใช้ได้ทั้งคอมพิวเตอร์และมือถือ</p>
    </div>
    {% endif %}
    
    <div class="card">
        <h2>🔗 สร้างลิงก์ติดตาม</h2>
        <div class="link-box">
            <h3>ลิงก์หลักสำหรับส่งให้คนอื่นคลิก:</h3>
            <div style="display: flex; gap: 10px; margin: 15px 0;">
                <input type="text" id="main-link" value="{{ main_link }}" readonly style="flex: 1;">
                <button onclick="copyLink()">คัดลอกลิงก์</button>
            </div>
            
            <h3>สร้างลิงก์พิเศษ:</h3>
            <div style="display: flex; gap: 10px; margin: 15px 0;">
                <input type="text" id="custom-name" placeholder="ตั้งชื่อลิงก์ (เช่น: งานเลี้ยง, ของขวัญ)">
                <button onclick="createCustomLink()">สร้างลิงก์</button>
            </div>
            <div id="custom-link" style="margin-top: 10px;"></div>
        </div>
    </div>
    
    <div class="stats">
        <div class="stat-item">
            <h3>👥 จำนวนคลิกทั้งหมด</h3>
            <p style="font-size: 32px; color: #2196F3;">{{ total_clicks }}</p>
        </div>
        <div class="stat-item">
            <h3>📱 อุปกรณ์ล่าสุด</h3>
            <p style="font-size: 24px;">{{ last_device }}</p>
        </div>
        <div class="stat-item">
            <h3>📍 ประเทศล่าสุด</h3>
            <p style="font-size: 24px;">{{ last_country }}</p>
        </div>
    </div>
    
    <div class="card">
        <h2>📊 จัดการข้อมูล</h2>
        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
            <button onclick="location.href='/logs'">📋 ดูบันทึกทั้งหมด</button>
            <button onclick="location.href='/live'">🔴 ดูแบบเรียลไทม์</button>
            <button onclick="location.href='/export-csv'">📥 ดาวน์โหลด CSV</button>
            <button onclick="location.href='/export-json'">📥 ดาวน์โหลด JSON</button>
            <button onclick="if(confirm('แน่ใจว่าต้องการล้างข้อมูลทั้งหมด?')) location.href='/clear'" style="background: #dc3545;">🗑️ ล้างข้อมูลทั้งหมด</button>
        </div>
    </div>
    
    <div class="card">
        <h2>🔄 ทดสอบระบบ</h2>
        <p>ทดสอบด้วยตัวเองก่อนส่งให้คนอื่น:</p>
        <div style="display: flex; gap: 10px;">
            <button onclick="testClick('test')">คลิกทดสอบจากอุปกรณ์นี้</button>
            <button onclick="window.open('{{ main_link }}', '_blank')">เปิดลิงก์ในแท็บใหม่</button>
            <button onclick="testDifferentIPs()">ทดสอบหลาย IP</button>
        </div>
    </div>
    
    <div class="warning">
        <h3>⚠️ ข้อควรระวัง</h3>
        <p>1. ระบบนี้แสดงตำแหน่งโดยประมาณจาก IP เท่านั้น (คลาดเคลื่อน 10-50 กม.)</p>
        <p>2. ใช้สำหรับการเรียนรู้เท่านั้น ห้ามใช้ละเมิดความเป็นส่วนตัวผู้อื่น</p>
        <p>3. ข้อมูลบันทึกในระบบชั่วคราว</p>
        <p>4. บน Render.com ข้อมูลอาจถูกล้างเมื่อเซิร์ฟเวอร์รีสตาร์ต</p>
    </div>
    
    <div class="card">
        <h3>📡 ข้อมูลระบบ</h3>
        <p>🟢 เซิร์ฟเวอร์: Render.com</p>
        <p>🔗 URL หลัก: {{ main_link }}</p>
        <p>📊 ดูบันทึก: <a href="/logs">/logs</a></p>
        <p>🕒 เวลาเริ่มต้น: {{ start_time }}</p>
    </div>
    
    <script>
    function copyLink() {
        const link = document.getElementById('main-link');
        link.select();
        document.execCommand('copy');
        alert('✅ คัดลอกลิงก์เรียบร้อยแล้ว!');
    }
    
    function createCustomLink() {
        const name = document.getElementById('custom-name').value.trim();
        if (!name) return alert('❌ กรุณากรอกชื่อลิงก์');
        const base = "{{ main_link }}".replace('/click/main', '');
        const customLink = base + '/click/' + encodeURIComponent(name);
        
        document.getElementById('custom-link').innerHTML = 
            `<div class="link-box">
                <p><strong>ลิงก์ที่สร้าง:</strong></p>
                <div style="display: flex; gap: 10px;">
                    <input value="${customLink}" readonly style="flex: 1;">
                    <button onclick="navigator.clipboard.writeText('${customLink}');alert('คัดลอกแล้ว!')">คัดลอก</button>
                </div>
                <p style="margin-top: 10px;"><small>ลิงก์นี้จะบันทึกข้อมูลเมื่อมีคนคลิก</small></p>
            </div>`;
    }
    
    function testClick(linkName) {
        fetch('/click/' + linkName)
            .then(() => alert('✅ บันทึกการทดสอบเรียบร้อย!\nไปดูผลที่หน้า /logs'))
            .catch(err => alert('❌ เกิดข้อผิดพลาด: ' + err));
    }
    
    function testDifferentIPs() {
        const tests = ['local-test', 'mobile-test', 'vpn-test'];
        tests.forEach(test => {
            fetch('/click/' + test);
        });
        alert('🧪 กำลังทดสอบหลายสถานการณ์...');
    }
    </script>
</body>
</html>
'''

HTML_CLICK = '''
<!DOCTYPE html>
<html>
<head>
    <title>ขอบคุณที่คลิก! 🙏</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: 'Segoe UI', 'Sukhumvit Set', sans-serif; 
            text-align: center; 
            padding: 20px; 
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container { 
            background: white; 
            padding: 30px; 
            border-radius: 20px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.1); 
            max-width: 90%;
            width: 500px;
        }
        .checkmark { 
            color: #4CAF50; 
            font-size: 60px; 
            margin-bottom: 15px;
        }
        .info-card { 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 15px; 
            text-align: left;
            margin: 20px 0;
            border-left: 5px solid #2196F3;
        }
        .info-item { margin: 8px 0; }
        .ip-address { 
            font-family: monospace; 
            font-size: 16px; 
            color: #d32f2f; 
            font-weight: bold;
            background: #ffebee;
            padding: 6px 12px;
            border-radius: 5px;
            display: inline-block;
        }
        .location-detail { color: #666; font-size: 0.9em; }
        .countdown {
            margin-top: 25px;
            padding: 15px;
            background: #e8f5e9;
            border-radius: 10px;
            color: #2e7d32;
            font-weight: bold;
        }
        @media (max-width: 480px) {
            .container { padding: 20px; }
            .info-card { padding: 15px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✓</div>
        <h1>ขอบคุณที่คลิก! 🙏</h1>
        <p>บันทึกข้อมูลเรียบร้อยแล้ว</p>
        
        <div class="info-card">
            <div class="info-item">
                <strong>🌐 IP Address:</strong><br>
                <span class="ip-address">{{ ip }}</span>
            </div>
            
            <div class="info-item">
                <strong>📱 อุปกรณ์:</strong><br>
                {{ device }}
            </div>
            
            <div class="info-item">
                <strong>📍 ตำแหน่งโดยประมาณ:</strong><br>
                <div class="location-detail">
                    {% if location.country == 'ไทย' %}
                        ประเทศ: {{ location.country }}<br>
                        {% if location.region and location.region != 'Unknown' %}
                            จังหวัด: {{ location.region }}<br>
                        {% endif %}
                        {% if location.city and location.city != 'Unknown' %}
                            อำเภอ/เขต: {{ location.city }}<br>
                        {% endif %}
                        {% if location.district and location.district != 'Unknown' %}
                            ตำบล/แขวง: {{ location.district }}<br>
                        {% endif %}
                        <em style="color: #888; font-size: 0.85em;">(ตำแหน่งโดยประมาณจาก IP)</em>
                    {% else %}
                        ประเทศ: {{ location.country }}<br>
                        {% if location.city and location.city != 'Unknown' %}
                            เมือง: {{ location.city }}<br>
                        {% endif %}
                    {% endif %}
                </div>
            </div>
            
            <div class="info-item">
                <strong>🕒 เวลา:</strong><br>
                {{ time }}
            </div>
        </div>
        
        <div class="countdown" id="countdown-display">
            หน้าต่างนี้จะปิดอัตโนมัติใน <span id="countdown">5</span> วินาที
        </div>
    </div>
    
    <script>
        // นับถอยหลังและปิดหน้าต่าง
        let countdown = 5;
        const countdownElement = document.getElementById('countdown');
        
        const interval = setInterval(() => {
            countdown--;
            countdownElement.textContent = countdown;
            
            if (countdown <= 0) {
                clearInterval(interval);
                
                // พยายามปิดหน้าต่าง
                if (window.history.length > 1) {
                    window.history.back();
                } else if (window.opener) {
                    window.close();
                } else {
                    // ถ้าไม่สามารถปิดได้
                    document.getElementById('countdown-display').innerHTML = 
                        '<div style="color: #4CAF50;">✔️ บันทึกข้อมูลเรียบร้อยแล้ว</div>';
                }
            }
        }, 1000);
        
        // พยายามปิดหน้าต่างทันทีถ้าเปิดจาก popup
        setTimeout(() => {
            if (window.opener) {
                window.close();
            }
        }, 100);
    </script>
</body>
</html>
'''

# HTML_LOGS และ HTML_LIVE เหมือนเดิม (ไม่อัพเดตที่นี่เพื่อความกะทัดรัด)
# ให้คง HTML_LOGS และ HTML_LIVE ไว้เหมือนเดิม

# ============================================
# LOCATION FUNCTIONS (ปรับ timeout)
# ============================================

def get_location(ip):
    """แปลง IP เป็นตำแหน่งแบบละเอียด"""
    try:
        # ถ้าเป็น IP local
        if ip.startswith('127.') or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
            return {
                'country': 'Local',
                'country_code': 'LOCAL',
                'region': 'Local Network',
                'city': 'เครือข่ายภายใน',
                'district': 'ไม่ระบุ',
                'subdistrict': 'ไม่ระบุ',
                'postal': 'ไม่ระบุ',
                'isp': 'Local Network',
                'lat': None,
                'lon': None,
                'address': 'เครือข่ายภายใน (ไม่สามารถระบุที่อยู่ได้)'
            }
        
        # ใช้ ip-api.com (ฟรี) - ลด timeout สำหรับ Render
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,district,zip,lat,lon,isp,org,as,query',
                timeout=3  # ลด timeout
            )
            data = response.json()
            
            if data.get('status') == 'success':
                # แปลงชื่อจังหวัดเป็นไทย
                regions_th = {
                    'Bangkok': 'กรุงเทพมหานคร',
                    'Chiang Mai': 'เชียงใหม่',
                    'Phuket': 'ภูเก็ต',
                    'Samut Prakan': 'สมุทรปราการ',
                    'Nonthaburi': 'นนทบุรี',
                    'Udon Thani': 'อุดรธานี',
                    'Chon Buri': 'ชลบุรี',
                    'Nakhon Ratchasima': 'นครราชสีมา',
                    'Khon Kaen': 'ขอนแก่น',
                    'Songkhla': 'สงขลา',
                    'Pathum Thani': 'ปทุมธานี',
                    'Nakhon Si Thammarat': 'นครศรีธรรมราช',
                    'Surat Thani': 'สุราษฎร์ธานี',
                    'Rayong': 'ระยอง',
                    'Lampang': 'ลำปาง',
                    'Samut Sakhon': 'สมุทรสาคร',
                    'Nakhon Pathom': 'นครปฐม',
                    'Ayutthaya': 'พระนครศรีอยุธยา',
                    'Chiang Rai': 'เชียงราย',
                    'Trang': 'ตรัง',
                    'Pattaya': 'พัทยา',
                    'Hat Yai': 'หาดใหญ่',
                    'Nakhon Sawan': 'นครสวรรค์',
                    'Ubon Ratchathani': 'อุบลราชธานี',
                    'Surin': 'สุรินทร์',
                    'Mae Hong Son': 'แม่ฮ่องสอน',
                    'Kanchanaburi': 'กาญจนบุรี',
                    'Hua Hin': 'หัวหิน',
                    'Phetchaburi': 'เพชรบุรี'
                }
                
                country = data.get('country', 'Unknown')
                region = data.get('regionName', '')
                city = data.get('city', '')
                district = data.get('district', '')
                postal = data.get('zip', '')
                
                # แปลงชื่อจังหวัดเป็นไทยถ้าจังหวัดอยู่ในไทย
                if country == 'Thailand' and region in regions_th:
                    region_th = regions_th[region]
                    country_th = 'ไทย'
                elif country == 'Thailand':
                    region_th = region
                    country_th = 'ไทย'
                else:
                    region_th = region
                    country_th = country
                
                # สร้างที่อยู่แบบละเอียด
                address_parts = []
                if district and district != city:
                    address_parts.append(f"ตำบล/แขวง {district}")
                if city:
                    address_parts.append(f"อำเภอ/เขต {city}")
                if region_th:
                    address_parts.append(f"จังหวัด {region_th}")
                if postal:
                    address_parts.append(f"รหัสไปรษณีย์ {postal}")
                
                full_address = ", ".join(address_parts) if address_parts else "ไม่สามารถระบุที่อยู่ได้"
                
                return {
                    'country': country_th if country == 'Thailand' else country,
                    'country_code': data.get('countryCode', ''),
                    'region': region_th,
                    'city': city,
                    'district': district,
                    'subdistrict': district,
                    'postal': postal,
                    'isp': data.get('isp', 'Unknown'),
                    'org': data.get('org', ''),
                    'lat': data.get('lat'),
                    'lon': data.get('lon'),
                    'address': full_address,
                    'raw_data': data
                }
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout ในการขอข้อมูลตำแหน่งจาก IP: {ip}")
        
        # ถ้า ip-api.com ล้มเหลว ให้ใช้ api อื่น
        return get_location_backup(ip)
            
    except Exception as e:
        print(f"Error getting location: {e}")
        return get_location_backup(ip)

def get_location_backup(ip):
    """API สำรองสำหรับหาตำแหน่ง"""
    try:
        # ใช้ ipapi.co เป็น backup
        response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2)
        data = response.json()
        
        country = data.get('country_name', 'Unknown')
        
        return {
            'country': 'ไทย' if country == 'Thailand' else country,
            'country_code': data.get('country_code', ''),
            'region': data.get('region', 'Unknown'),
            'city': data.get('city', 'Unknown'),
            'district': data.get('district', 'Unknown'),
            'subdistrict': data.get('subdistrict', 'Unknown'),
            'postal': data.get('postal', 'Unknown'),
            'isp': data.get('org', 'Unknown'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'address': f"{data.get('city', '')}, {data.get('region', '')}, {country}"
        }
    except:
        return {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'district': 'Unknown',
            'subdistrict': 'Unknown',
            'postal': 'Unknown',
            'isp': 'Unknown',
            'lat': None,
            'lon': None,
            'address': 'ไม่สามารถระบุที่อยู่ได้'
        }

def detect_device(user_agent):
    """ตรวจสอบอุปกรณ์จาก User-Agent"""
    ua = user_agent.lower()
    
    # ตรวจสอบอุปกรณ์
    if 'mobile' in ua:
        device = '📱'
    elif 'tablet' in ua:
        device = '📱'
    elif 'android' in ua:
        device = '📱'
    elif 'iphone' in ua or 'ipad' in ua or 'ipod' in ua:
        device = '📱'
    elif 'windows' in ua:
        device = '💻'
    elif 'mac' in ua:
        device = '🍎'
    elif 'linux' in ua:
        device = '🐧'
    elif 'bot' in ua or 'crawler' in ua or 'spider' in ua:
        device = '🤖'
    else:
        device = '🖥️'
    
    # ตรวจสอบ OS
    if 'windows' in ua:
        os_name = 'Windows'
    elif 'mac' in ua:
        os_name = 'Mac'
    elif 'android' in ua:
        os_name = 'Android'
    elif 'ios' in ua or 'iphone' in ua:
        os_name = 'iOS'
    elif 'linux' in ua:
        os_name = 'Linux'
    else:
        os_name = 'Unknown OS'
    
    # ตรวจสอบเบราว์เซอร์
    if 'chrome' in ua and 'chromium' not in ua:
        browser = 'Chrome'
    elif 'firefox' in ua:
        browser = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        browser = 'Safari'
    elif 'edge' in ua:
        browser = 'Edge'
    elif 'opera' in ua:
        browser = 'Opera'
    else:
        browser = 'Unknown Browser'
    
    return f"{device} {os_name} ({browser})"

# ============================================
# FLASK ROUTES
# ============================================

@app.route('/')
def home():
    """หน้าหลัก"""
    # ตรวจสอบว่าใช้งานบน Render หรือไม่
    is_render = 'render.com' in request.host_url
    
    main_link = request.host_url + "click/main"
    
    # คำนวณสถิติ
    thai_count = sum(1 for log in logs if log['location']['country'] == 'ไทย')
    mobile_count = sum(1 for log in logs if '📱' in log['device'])
    
    return render_template_string(HTML_HOME, 
                                main_link=main_link,
                                is_render=is_render,
                                render_url=request.host_url.rstrip('/'),
                                total_clicks=len(logs),
                                last_device=logs[-1]['device'] if logs else 'ไม่มีข้อมูล',
                                last_country=logs[-1]['location']['country'] if logs else 'ไม่มีข้อมูล',
                                thai_count=thai_count,
                                mobile_count=mobile_count,
                                start_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/click/<link_name>')
def track_click(link_name):
    """บันทึกเมื่อมีคนคลิก"""
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # ตรวจสอบอุปกรณ์
    device = detect_device(user_agent)
    
    # ตรวจสอบตำแหน่งแบบละเอียด
    location = get_location(ip)
    
    # สร้างข้อมูล
    log_entry = {
        'ip': ip,
        'device': device,
        'user_agent': user_agent[:100],
        'link_name': link_name,
        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'location': location
    }
    
    # บันทึกลง memory
    logs.append(log_entry)
    
    # แสดงใน console
    print(f"[{log_entry['time']}] 📍 Click from {ip} - {location['country']} - {device}")
    
    # บันทึกลงไฟล์
    save_logs_to_file()
    
    return render_template_string(HTML_CLICK, 
                                 ip=ip, 
                                 device=device, 
                                 time=log_entry['time'],
                                 location=location)

@app.route('/logs')
def view_logs():
    """ดูบันทึกทั้งหมด"""
    # เรียงจากใหม่ไปเก่า
    sorted_logs = sorted(logs, key=lambda x: x['time'], reverse=True)
    return render_template_string(HTML_LOGS, 
                                 logs=sorted_logs,
                                 count=len(logs))

@app.route('/live')
def live_view():
    """หน้าดูแบบเรียลไทม์"""
    recent_logs = sorted(logs, key=lambda x: x['time'], reverse=True)[:20]
    
    # คำนวณสถิติ
    thai_clicks = sum(1 for log in logs if log['location']['country'] == 'ไทย')
    mobile_clicks = sum(1 for log in logs if '📱' in log['device'])
    
    return render_template_string(HTML_LIVE,
                                 recent_logs=recent_logs,
                                 total_clicks=len(logs),
                                 thai_clicks=thai_clicks,
                                 mobile_clicks=mobile_clicks)

@app.route('/export-csv')
def export_csv():
    """Export ข้อมูลเป็น CSV"""
    si = StringIO()
    writer = csv.writer(si)
    
    # เขียน header
    writer.writerow([
        'เวลา', 'IP Address', 'ประเทศ', 'จังหวัด', 'อำเภอ/เขต', 
        'ตำบล/แขวง', 'รหัสไปรษณีย์', 'ISP', 'อุปกรณ์', 'ละติจูด', 'ลองจิจูด', 'ที่อยู่เต็ม'
    ])
    
    # เขียนข้อมูล
    for log in logs:
        writer.writerow([
            log['time'],
            log['ip'],
            log['location']['country'],
            log['location']['region'],
            log['location']['city'],
            log['location']['district'],
            log['location']['postal'],
            log['location']['isp'],
            log['device'],
            log['location']['lat'],
            log['location']['lon'],
            log['location']['address']
        ])
    
    output = si.getvalue()
    
    # ส่งไฟล์ CSV กลับ
    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=ip_logs.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

@app.route('/export-json')
def export_json():
    """Export ข้อมูลเป็น JSON"""
    import json as json_module
    
    # สร้างข้อมูล JSON
    export_data = {
        'export_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_records': len(logs),
        'logs': logs
    }
    
    # ส่งไฟล์ JSON กลับ
    response = make_response(json_module.dumps(export_data, indent=2, ensure_ascii=False))
    response.headers["Content-Disposition"] = "attachment; filename=ip_logs.json"
    response.headers["Content-type"] = "application/json; charset=utf-8"
    return response

@app.route('/clear')
def clear_logs():
    """ล้างข้อมูลทั้งหมด"""
    global logs
    logs.clear()
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    print("\n🗑️ ล้างข้อมูลทั้งหมดเรียบร้อย")
    return redirect('/')

@app.route('/health')
def health_check():
    """Health check สำหรับ Render"""
    return {"status": "healthy", "logs_count": len(logs)}, 200

def save_logs_to_file():
    """บันทึก logs ลงไฟล์"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving logs: {e}")

def load_logs_from_file():
    """โหลด logs จากไฟล์"""
    global logs
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                loaded_logs = json.load(f)
                logs.extend(loaded_logs)
                print(f"📂 โหลดบันทึก {len(loaded_logs)} รายการจากไฟล์")
    except Exception as e:
        print(f"Error loading logs: {e}")

def print_startup_info():
    """แสดงข้อมูลเมื่อเริ่มต้นเซิร์ฟเวอร์"""
    print("\n" + "="*70)
    print("🚀 IP Tracker สำหรับ Render.com")
    print("="*70)
    print(f"📁 ไฟล์ข้อมูล: {DATA_FILE}")
    print(f"📊 ข้อมูลที่มีอยู่: {len(logs)} รายการ")
    print("="*70)
    print("⚠️  สำหรับการเรียนรู้เท่านั้น!")
    print("📌 ระบบจะทำงานบน: https://your-app-name.onrender.com")
    print("📌 Health check: /health")
    print("="*70)

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == '__main__':
    # โหลดข้อมูลเก่าจากไฟล์
    load_logs_from_file()
    
    # แสดงข้อมูลเริ่มต้น
    print_startup_info()
    
    # รันแอปพลิเคชัน
    # บน Render ต้องใช้ port จาก environment variable
    app.run(host=HOST, port=PORT, debug=False)

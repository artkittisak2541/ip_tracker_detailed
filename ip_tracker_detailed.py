from flask import Flask, request, render_template_string, redirect, make_response
import datetime
import json
import os
import requests
import socket
import threading
import webbrowser
import csv
from io import StringIO

app = Flask(__name__)

# เก็บข้อมูลใน memory
logs = []

# ============================================
# HTML TEMPLATES
# ============================================

HTML_HOME = '''
<!DOCTYPE html>
<html>
<head>
    <title>🖥️ IP Tracker แสดงที่อยู่ละเอียด</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
    </style>
</head>
<body>
    <div class="header">
        <h1>🌍 IP Tracker แสดงที่อยู่ละเอียด</h1>
        <p>ติดตามตำแหน่งโดยประมาณจาก IP Address</p>
    </div>
    
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
        <p>3. บันทึกข้อมูลอัตโนมัติในไฟล์ click_logs.json</p>
    </div>
    
    <div class="card">
        <h3>📡 ข้อมูลเซิร์ฟเวอร์</h3>
        <p>🟢 เซิร์ฟเวอร์ทำงานอยู่ที่: <span class="ip-display">{{ server_ip }}</span></p>
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
        // ทดสอบหลายสถานการณ์
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
            padding: 40px; 
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        .container { 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.1); 
            display: inline-block;
            max-width: 600px;
        }
        .checkmark { 
            color: #4CAF50; 
            font-size: 80px; 
            margin-bottom: 20px;
        }
        .info-card { 
            background: #f8f9fa; 
            padding: 25px; 
            border-radius: 15px; 
            text-align: left;
            margin: 25px 0;
            border-left: 5px solid #2196F3;
        }
        .info-item { margin: 10px 0; }
        .ip-address { 
            font-family: monospace; 
            font-size: 18px; 
            color: #d32f2f; 
            font-weight: bold;
            background: #ffebee;
            padding: 8px 15px;
            border-radius: 5px;
            display: inline-block;
        }
        .location-detail { color: #666; font-size: 0.95em; }
        .btn { 
            background: #2196F3; 
            color: white; 
            padding: 12px 25px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 10px;
        }
        .btn:hover { background: #1976D2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✓</div>
        <h1>ขอบคุณที่คลิก! 🙏</h1>
        <p>บันทึกข้อมูลของคุณเรียบร้อยแล้ว</p>
        
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
                        {% if location.postal and location.postal != 'Unknown' %}
                            รหัสไปรษณีย์: {{ location.postal }}<br>
                        {% endif %}
                        <em style="color: #888; font-size: 0.9em;">(ตำแหน่งโดยประมาณจาก IP)</em>
                    {% else %}
                        ประเทศ: {{ location.country }}<br>
                        {% if location.city and location.city != 'Unknown' %}
                            เมือง: {{ location.city }}<br>
                        {% endif %}
                        {% if location.region and location.region != 'Unknown' %}
                            รัฐ/จังหวัด: {{ location.region }}
                        {% endif %}
                    {% endif %}
                </div>
            </div>
            
            <div class="info-item">
                <strong>🕒 เวลา:</strong><br>
                {{ time }}
            </div>
            
            <div class="info-item">
                <strong>📡 เครือข่าย:</strong><br>
                {{ location.isp }}
            </div>
        </div>
        
        <p style="margin-top: 30px;">
            <a href="/" class="btn">← กลับหน้าหลัก</a>
            {% if location.lat and location.lon %}
            <a href="https://maps.google.com/?q={{ location.lat }},{{ location.lon }}" target="_blank" class="btn">🗺️ ดูแผนที่</a>
            {% endif %}
        </p>
        
        <div style="margin-top: 30px; padding: 15px; background: #e8f5e9; border-radius: 10px; color: #2e7d32;">
            <p><strong>ℹ️ ข้อมูล:</strong> ระบบนี้บันทึกข้อมูลเพื่อการเรียนรู้เท่านั้น</p>
            <p style="font-size: 0.9em;">ตำแหน่งที่แสดงเป็นตำแหน่งโดยประมาณจากผู้ให้บริการอินเทอร์เน็ต</p>
        </div>
    </div>
    
    <script>
        // ปิดหน้าต่างอัตโนมัติถ้าเป็น popup
        if(window.opener) {
            setTimeout(() => {
                window.close();
            }, 5000);
        }
        
        // แสดงเวลา countdown ถ้าเป็น popup
        if(window.opener) {
            let countdown = 5;
            const countdownEl = document.createElement('p');
            countdownEl.innerHTML = `หน้าต่างนี้จะปิดอัตโนมัติใน <span id="countdown">${countdown}</span> วินาที`;
            countdownEl.style.marginTop = '20px';
            countdownEl.style.color = '#666';
            document.querySelector('.container').appendChild(countdownEl);
            
            const interval = setInterval(() => {
                countdown--;
                document.getElementById('countdown').textContent = countdown;
                if(countdown <= 0) {
                    clearInterval(interval);
                    window.close();
                }
            }, 1000);
        }
    </script>
</body>
</html>
'''

HTML_LOGS = '''
<!DOCTYPE html>
<html>
<head>
    <title>📊 บันทึกการคลิกทั้งหมด</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { font-family: 'Segoe UI', 'Sukhumvit Set', sans-serif; }
        body { margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px; margin-bottom: 25px; }
        .controls { background: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        button { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; }
        button:hover { background: #1976D2; }
        .export-btn { background: #4CAF50; }
        .clear-btn { background: #dc3545; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
        th { background: #343a40; color: white; padding: 15px; text-align: left; }
        td { padding: 15px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f8f9fa; }
        .ip-cell { font-family: monospace; font-weight: bold; color: #d32f2f; }
        .location-cell { max-width: 300px; }
        .address-detail { font-size: 0.9em; color: #666; }
        .badge { background: #6c757d; color: white; padding: 3px 10px; border-radius: 20px; font-size: 0.85em; display: inline-block; margin: 2px; }
        .map-link { color: #2196F3; text-decoration: none; }
        .map-link:hover { text-decoration: underline; }
        .pagination { margin-top: 20px; display: flex; justify-content: center; gap: 10px; }
        .page-btn { padding: 8px 15px; background: #6c757d; color: white; border-radius: 5px; cursor: pointer; }
        .page-btn.active { background: #2196F3; }
        .no-data { text-align: center; padding: 50px; color: #666; }
        .device-icon { font-size: 1.2em; margin-right: 5px; }
        .filter-bar { display: flex; gap: 10px; margin-bottom: 15px; }
        .filter-bar input, .filter-bar select { padding: 8px; border: 1px solid #ddd; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 บันทึกการคลิกทั้งหมด</h1>
        <p>แสดงข้อมูลตำแหน่งละเอียดจาก IP Address</p>
    </div>
    
    <div class="controls">
        <button onclick="location.href='/'">← กลับหน้าหลัก</button>
        <button onclick="location.href='/live'">🔴 Live View</button>
        <button onclick="location.href='/export-csv'" class="export-btn">📥 Export CSV</button>
        <button onclick="location.href='/export-json'" class="export-btn">📥 Export JSON</button>
        <button onclick="if(confirm('ลบข้อมูลทั้งหมด?')) location.href='/clear'" class="clear-btn">🗑️ ล้างข้อมูลทั้งหมด</button>
        
        <div style="margin-left: auto; display: flex; gap: 10px; align-items: center;">
            <input type="text" id="search-ip" placeholder="ค้นหา IP..." style="padding: 8px;">
            <select id="filter-country">
                <option value="">ทั้งหมด</option>
                <option value="ไทย">ไทย</option>
                <option value="อื่นๆ">อื่นๆ</option>
            </select>
            <button onclick="applyFilters()">ค้นหา</button>
        </div>
    </div>
    
    {% if logs %}
    <div class="filter-bar">
        <span>แสดง:</span>
        <select id="rows-per-page" onchange="changeRowsPerPage()">
            <option value="20">20 แถว</option>
            <option value="50">50 แถว</option>
            <option value="100">100 แถว</option>
            <option value="all">ทั้งหมด</option>
        </select>
        <span style="margin-left: auto;">พบทั้งหมด {{ count }} รายการ</span>
    </div>
    
    <table id="logs-table">
        <thead>
            <tr>
                <th>เวลา</th>
                <th>IP Address</th>
                <th class="location-cell">📍 ที่อยู่ละเอียด</th>
                <th>อุปกรณ์</th>
                <th>เครือข่าย</th>
                <th>แผนที่</th>
            </tr>
        </thead>
        <tbody>
            {% for log in logs %}
            <tr>
                <td>{{ log.time }}</td>
                <td class="ip-cell">{{ log.ip }}</td>
                <td class="location-cell">
                    <div class="address-detail">
                        <strong>{{ log.location.country }}</strong>
                        {% if log.location.country == 'ไทย' %}
                            <br>
                            {% if log.location.region and log.location.region != 'Unknown' %}
                                <small>จังหวัด: {{ log.location.region }}</small><br>
                            {% endif %}
                            {% if log.location.city and log.location.city != 'Unknown' %}
                                <small>อำเภอ/เขต: {{ log.location.city }}</small><br>
                            {% endif %}
                            {% if log.location.district and log.location.district != 'Unknown' %}
                                <small>ตำบล/แขวง: {{ log.location.district }}</small><br>
                            {% endif %}
                            {% if log.location.postal and log.location.postal != 'Unknown' %}
                                <small>รหัสไปรษณีย์: {{ log.location.postal }}</small>
                            {% endif %}
                            <br>
                            <em style="color: #888; font-size: 0.85em;">{{ log.location.address }}</em>
                        {% else %}
                            <br>
                            {% if log.location.city and log.location.city != 'Unknown' %}
                                <small>เมือง: {{ log.location.city }}</small><br>
                            {% endif %}
                            {% if log.location.region and log.location.region != 'Unknown' %}
                                <small>รัฐ/จังหวัด: {{ log.location.region }}</small>
                            {% endif %}
                        {% endif %}
                    </div>
                </td>
                <td>
                    <span class="device-icon">{{ log.device[:2] }}</span>
                    {{ log.device[2:] }}
                </td>
                <td><small>{{ log.location.isp[:25] }}{% if log.location.isp|length > 25 %}...{% endif %}</small></td>
                <td>
                    {% if log.location.lat and log.location.lon %}
                    <a class="map-link" href="https://maps.google.com/?q={{ log.location.lat }},{{ log.location.lon }}" target="_blank">
                        ดูแผนที่
                    </a>
                    {% else %}
                    <small>-</small>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="pagination" id="pagination">
        <!-- Pagination จะถูกสร้างด้วย JavaScript -->
    </div>
    
    {% else %}
    <div class="no-data">
        <h2>📭 ยังไม่มีบันทึกการคลิก</h2>
        <p>ลองส่งลิงก์ให้เพื่อนหรือทดสอบคลิกเองจากหน้าหลัก</p>
        <button onclick="location.href='/'">ไปหน้าหลัก</button>
    </div>
    {% endif %}
    
    <script>
    let currentPage = 1;
    let rowsPerPage = 20;
    let filteredLogs = {{ logs|tojson }};
    
    function applyFilters() {
        const searchIP = document.getElementById('search-ip').value.toLowerCase();
        const filterCountry = document.getElementById('filter-country').value;
        
        filteredLogs = {{ logs|tojson }}.filter(log => {
            let match = true;
            
            if (searchIP) {
                match = match && log.ip.toLowerCase().includes(searchIP);
            }
            
            if (filterCountry === 'ไทย') {
                match = match && log.location.country === 'ไทย';
            } else if (filterCountry === 'อื่นๆ') {
                match = match && log.location.country !== 'ไทย';
            }
            
            return match;
        });
        
        currentPage = 1;
        renderTable();
    }
    
    function changeRowsPerPage() {
        const select = document.getElementById('rows-per-page');
        rowsPerPage = select.value === 'all' ? filteredLogs.length : parseInt(select.value);
        currentPage = 1;
        renderTable();
    }
    
    function renderTable() {
        const tbody = document.querySelector('#logs-table tbody');
        if (!tbody) return;
        
        const start = (currentPage - 1) * rowsPerPage;
        const end = start + rowsPerPage;
        const pageLogs = filteredLogs.slice(start, end);
        
        tbody.innerHTML = '';
        pageLogs.forEach(log => {
            const row = tbody.insertRow();
            
            // เวลา
            row.insertCell().textContent = log.time;
            
            // IP
            const ipCell = row.insertCell();
            ipCell.className = 'ip-cell';
            ipCell.textContent = log.ip;
            
            // ที่อยู่
            const locCell = row.insertCell();
            locCell.className = 'location-cell';
            locCell.innerHTML = `
                <div class="address-detail">
                    <strong>${log.location.country}</strong>
                    ${log.location.country === 'ไทย' ? 
                        `<br>
                        ${log.location.region && log.location.region !== 'Unknown' ? `<small>จังหวัด: ${log.location.region}</small><br>` : ''}
                        ${log.location.city && log.location.city !== 'Unknown' ? `<small>อำเภอ/เขต: ${log.location.city}</small><br>` : ''}
                        ${log.location.district && log.location.district !== 'Unknown' ? `<small>ตำบล/แขวง: ${log.location.district}</small><br>` : ''}
                        ${log.location.postal && log.location.postal !== 'Unknown' ? `<small>รหัสไปรษณีย์: ${log.location.postal}</small><br>` : ''}
                        <br>
                        <em style="color: #888; font-size: 0.85em;">${log.location.address}</em>`
                    : 
                        `<br>
                        ${log.location.city && log.location.city !== 'Unknown' ? `<small>เมือง: ${log.location.city}</small><br>` : ''}
                        ${log.location.region && log.location.region !== 'Unknown' ? `<small>รัฐ/จังหวัด: ${log.location.region}</small>` : ''}`
                    }
                </div>
            `;
            
            // อุปกรณ์
            const deviceCell = row.insertCell();
            deviceCell.innerHTML = `<span class="device-icon">${log.device.slice(0,2)}</span>${log.device.slice(2)}`;
            
            // เครือข่าย
            const ispCell = row.insertCell();
            ispCell.innerHTML = `<small>${log.location.isp.slice(0,25)}${log.location.isp.length > 25 ? '...' : ''}</small>`;
            
            // แผนที่
            const mapCell = row.insertCell();
            if (log.location.lat && log.location.lon) {
                mapCell.innerHTML = `<a class="map-link" href="https://maps.google.com/?q=${log.location.lat},${log.location.lon}" target="_blank">ดูแผนที่</a>`;
            } else {
                mapCell.innerHTML = '<small>-</small>';
            }
        });
        
        renderPagination();
    }
    
    function renderPagination() {
        const totalPages = Math.ceil(filteredLogs.length / rowsPerPage);
        const paginationDiv = document.getElementById('pagination');
        if (!paginationDiv) return;
        
        paginationDiv.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        // ปุ่มก่อนหน้า
        if (currentPage > 1) {
            const prevBtn = document.createElement('span');
            prevBtn.className = 'page-btn';
            prevBtn.textContent = '← ก่อนหน้า';
            prevBtn.onclick = () => {
                currentPage--;
                renderTable();
            };
            paginationDiv.appendChild(prevBtn);
        }
        
        // ปุ่มหมายเลขหน้า
        const maxPagesToShow = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
        let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
        
        if (endPage - startPage + 1 < maxPagesToShow) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('span');
            pageBtn.className = 'page-btn' + (i === currentPage ? ' active' : '');
            pageBtn.textContent = i;
            pageBtn.onclick = () => {
                currentPage = i;
                renderTable();
            };
            paginationDiv.appendChild(pageBtn);
        }
        
        // ปุ่มถัดไป
        if (currentPage < totalPages) {
            const nextBtn = document.createElement('span');
            nextBtn.className = 'page-btn';
            nextBtn.textContent = 'ถัดไป →';
            nextBtn.onclick = () => {
                currentPage++;
                renderTable();
            };
            paginationDiv.appendChild(nextBtn);
        }
        
        // แสดงข้อมูล
        const infoSpan = document.createElement('span');
        infoSpan.style.marginLeft = '20px';
        infoSpan.style.color = '#666';
        infoSpan.textContent = `แสดง ${filteredLogs.length} รายการ`;
        paginationDiv.appendChild(infoSpan);
    }
    
    // เริ่มต้น
    renderTable();
    </script>
</body>
</html>
'''

HTML_LIVE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔴 Live Click Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="3">
    <style>
        * { font-family: 'Consolas', 'Monaco', monospace; }
        body { margin: 0; padding: 20px; background: #000; color: #0f0; }
        .header { text-align: center; margin-bottom: 30px; }
        .log-entry { 
            background: #111; 
            padding: 15px; 
            margin: 10px 0; 
            border-left: 4px solid #0f0;
            border-radius: 5px;
            animation: fadeIn 0.5s;
        }
        .log-entry.new { 
            background: #003300; 
            border-left: 4px solid #ff0;
            animation: highlight 2s;
        }
        .ip { color: #ff6b6b; font-weight: bold; }
        .location { color: #4ecdc4; }
        .time { color: #888; font-size: 0.9em; }
        .stats { 
            background: #222; 
            padding: 15px; 
            margin: 20px 0; 
            border-radius: 10px;
            display: flex;
            justify-content: space-around;
        }
        .stat { text-align: center; }
        .stat-value { font-size: 24px; color: #0f0; }
        .stat-label { font-size: 12px; color: #888; }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes highlight {
            0% { background: #005500; }
            100% { background: #003300; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔴 LIVE CLICK MONITOR</h1>
        <p>Auto-refresh every 3 seconds | Last update: <span id="current-time"></span></p>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{{ total_clicks }}</div>
                <div class="stat-label">TOTAL CLICKS</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ thai_clicks }}</div>
                <div class="stat-label">FROM THAILAND</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ mobile_clicks }}</div>
                <div class="stat-label">MOBILE DEVICES</div>
            </div>
        </div>
    </div>
    
    <div id="live-logs">
        {% for log in recent_logs %}
        <div class="log-entry {% if loop.index <= 3 %}new{% endif %}">
            <div>
                <span class="time">[{{ log.time }}]</span>
                <span class="ip">{{ log.ip }}</span>
                <span class="location">
                    - {{ log.location.country }}
                    {% if log.location.country == 'ไทย' %}
                        / {{ log.location.region }}
                        {% if log.location.city != 'Unknown' %} / {{ log.location.city }}{% endif %}
                    {% else %}
                        {% if log.location.city != 'Unknown' %} / {{ log.location.city }}{% endif %}
                    {% endif %}
                </span>
            </div>
            <div style="margin-top: 5px; font-size: 0.9em;">
                📱 {{ log.device }} | 📡 {{ log.location.isp[:30] }}
            </div>
        </div>
        {% endfor %}
    </div>
    
    <script>
        document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
        
        // Auto scroll to top for new entries
        window.scrollTo(0, 0);
    </script>
</body>
</html>
'''

# ============================================
# LOCATION FUNCTIONS
# ============================================

def get_location(ip):
    """แปลง IP เป็นตำแหน่งแบบละเอียด"""
    try:
        # ถ้าเป็น IP local
        if ip.startswith('127.') or ip.startswith('192.168.') or ip.startswith('10.'):
            return {
                'country': 'ไทย',
                'country_code': 'TH',
                'region': 'Local Network',
                'city': 'เครือข่ายภายใน',
                'district': 'ไม่ระบุ',
                'subdistrict': 'ไม่ระบุ',
                'postal': 'ไม่ระบุ',
                'isp': 'Local Network',
                'lat': '13.7563',
                'lon': '100.5018',
                'address': 'เครือข่ายภายใน (ไม่สามารถระบุที่อยู่ได้)'
            }
        
        # ใช้ ip-api.com (ฟรี)
        response = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,district,zip,lat,lon,isp,org,as,query',
            timeout=5
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
        else:
            # ถ้า ip-api.com ล้มเหลว ให้ใช้ api อื่น
            return get_location_backup(ip)
            
    except Exception as e:
        print(f"Error getting location: {e}")
        return get_location_backup(ip)

def get_location_backup(ip):
    """API สำรองสำหรับหาตำแหน่ง"""
    try:
        # ใช้ ipapi.co เป็น backup
        response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=3)
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
    # หา IP ของ PC
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    
    main_link = f"http://{local_ip}:5000/click/main"
    
    # คำนวณสถิติ
    thai_count = sum(1 for log in logs if log['location']['country'] == 'ไทย')
    mobile_count = sum(1 for log in logs if '📱' in log['device'])
    
    return render_template_string(HTML_HOME, 
                                main_link=main_link,
                                server_ip=local_ip,
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
    
    # แสดงใน console แบบละเอียด
    print(f"\n{'='*80}")
    print(f"📍 NEW CLICK DETECTED - DETAILED LOCATION INFO")
    print(f"{'='*80}")
    print(f"📅 เวลา: {log_entry['time']}")
    print(f"🌐 IP Address: {ip}")
    print(f"📱 อุปกรณ์: {device}")
    print(f"🔗 ลิงก์ที่คลิก: {link_name}")
    print(f"")
    print(f"📍 ที่อยู่ละเอียด:")
    
    if location['country'] == 'ไทย':
        print(f"   ประเทศ: {location['country']}")
        if location['region'] and location['region'] != 'Unknown':
            print(f"   จังหวัด: {location['region']}")
        if location['city'] and location['city'] != 'Unknown':
            print(f"   อำเภอ/เขต: {location['city']}")
        if location['district'] and location['district'] != 'Unknown':
            print(f"   ตำบล/แขวง: {location['district']}")
        if location['postal'] and location['postal'] != 'Unknown':
            print(f"   รหัสไปรษณีย์: {location['postal']}")
        print(f"   ที่อยู่รวม: {location['address']}")
    else:
        print(f"   ประเทศ: {location['country']}")
        if location['city'] and location['city'] != 'Unknown':
            print(f"   เมือง: {location['city']}")
        if location['region'] and location['region'] != 'Unknown':
            print(f"   รัฐ/จังหวัด: {location['region']}")
    
    print(f"")
    print(f"📡 ข้อมูลเครือข่าย:")
    print(f"   ISP: {location['isp']}")
    if location['lat'] and location['lon']:
        print(f"   พิกัด: {location['lat']}, {location['lon']}")
        print(f"   Google Maps: https://maps.google.com/?q={location['lat']},{location['lon']}")
    
    print(f"{'='*80}\n")
    
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
    if os.path.exists('click_logs.json'):
        os.remove('click_logs.json')
    print("\n🗑️ ล้างข้อมูลทั้งหมดเรียบร้อย")
    return redirect('/')

def save_logs_to_file():
    """บันทึก logs ลงไฟล์"""
    try:
        with open('click_logs.json', 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving logs: {e}")

def load_logs_from_file():
    """โหลด logs จากไฟล์"""
    global logs
    try:
        if os.path.exists('click_logs.json'):
            with open('click_logs.json', 'r', encoding='utf-8') as f:
                loaded_logs = json.load(f)
                logs.extend(loaded_logs)
                print(f"📂 โหลดบันทึก {len(loaded_logs)} รายการจากไฟล์")
    except Exception as e:
        print(f"Error loading logs: {e}")

def get_network_info():
    """แสดงข้อมูลเครือข่าย"""
    print("\n" + "="*70)
    print("🌐 ข้อมูลเครือข่ายเซิร์ฟเวอร์")
    print("="*70)
    
    try:
        # หา IP Local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        print(f"📍 IP Local ของคุณ: {local_ip}")
        print(f"🔗 ลิงก์หลักสำหรับติดตาม: http://{local_ip}:5000/click/main")
        print(f"📊 ดูบันทึก: http://{local_ip}:5000/logs")
        print(f"🏠 หน้าแรก: http://{local_ip}:5000")
        
        # แสดง QR Code ถ้าเป็นไปได้
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=2, border=2)
            qr.add_data(f"http://{local_ip}:5000")
            qr.make(fit=True)
            print(f"📱 QR Code สำหรับเข้าถึง: http://{local_ip}:5000")
        except:
            pass
        
    except Exception as e:
        print(f"❌ ผิดพลาดในการหาข้อมูลเครือข่าย: {e}")
        print(f"📍 ใช้ localhost แทน: http://localhost:5000")
    
    print("="*70)

# ============================================
# SKIP NGROK WARNING (REMOVE FREE PLAN WARNING PAGE)
# ============================================
@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response    

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == '__main__':
    # โหลดข้อมูลเก่าจากไฟล์
    load_logs_from_file()
    
    # แสดงข้อมูลเครือข่าย
    get_network_info()
    
    # เปิดเบราว์เซอร์อัตโนมัติ
    try:
        threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    except:
        pass
    
    print("\n🚀 กำลังเริ่มเซิร์ฟเวอร์ IP Tracker...")
    print("⚠️  สำหรับการเรียนรู้เท่านั้น!")
    print("📌 กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์")
    print("\n" + "="*70)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\n🛑 หยุดเซิร์ฟเวอร์แล้ว")
        print(f"💾 บันทึกข้อมูลลงไฟล์...")
        save_logs_to_file()
        print(f"✅ บันทึก {len(logs)} รายการลงไฟล์เรียบร้อย")
        print("👋 สิ้นสุดการทำงาน")

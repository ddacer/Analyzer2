// Navigation Logic
const navBtns = document.querySelectorAll('.nav-btn');
const pages = document.querySelectorAll('.page');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        navBtns.forEach(b => b.classList.remove('active'));
        pages.forEach(p => p.classList.add('hidden'));
        pages.forEach(p => p.classList.remove('active'));
        
        btn.classList.add('active');
        const targetId = btn.getAttribute('data-target');
        const targetPage = document.getElementById(targetId);
        targetPage.classList.remove('hidden');
        
        void targetPage.offsetWidth;
        targetPage.classList.add('active');
        
        if (targetId === 'history-page') {
            loadHistory();
        } else if (targetId === 'compare-page') {
            loadCompareOptions();
        }
    });
});

// Toast System
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (type === 'error') {
        toast.style.borderLeftColor = 'var(--danger)';
    }
    toast.innerHTML = message;
    container.appendChild(toast);
    setTimeout(() => {
        if(container.contains(toast)) {
            container.removeChild(toast);
        }
    }, 3500);
}

// Expander logic
function attachExpanderEvents() {
    document.querySelectorAll('.expander-header').forEach(header => {
        const newHeader = header.cloneNode(true);
        header.parentNode.replaceChild(newHeader, header);
        
        newHeader.addEventListener('click', () => {
            const expander = newHeader.parentElement;
            expander.classList.toggle('open');
        });
    });
}

function renderExpanderList(title, items, icon) {
    let html = `<h4>${title}</h4>`;
    if (!items || items.length === 0) {
        return html + `<p style="color:var(--text-muted); margin-bottom: 1rem;">ไม่มีข้อมูลในหมวดนี้</p>`;
    }
    items.forEach(item => {
        const topic = item.topic || 'ไม่มีหัวข้อ';
        const details = item.details || 'ไม่มีรายละเอียด';
        html += `
        <div class="expander">
            <div class="expander-header">
                <span>${icon} ${topic}</span>
                <i class="fa-solid fa-chevron-down"></i>
            </div>
            <div class="expander-content">
                <p>${details}</p>
            </div>
        </div>`;
    });
    return html;
}

// Format numbers
const formatNumber = (num) => {
    return new Intl.NumberFormat('th-TH').format(num || 0);
};

let activeHeatmapChart = null;
let activeSentimentChart = null;

// =====================================
// Analyze Page
// =====================================
const analyzeBtn = document.getElementById('analyze-btn');
const analyzeInput = document.getElementById('video-url-input');
const analyzeLoading = document.getElementById('analyze-loading');
const analyzeResult = document.getElementById('analyze-result');

analyzeBtn.addEventListener('click', async () => {
    const url = analyzeInput.value.trim();
    if (!url) {
        showToast('กรุณาวางลิงก์ YouTube ก่อน', 'error');
        return;
    }

    analyzeResult.classList.add('hidden');
    analyzeLoading.classList.remove('hidden');

    try {
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_url: url })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'เกิดข้อผิดพลาดในการวิเคราะห์');
        }

        const data = await res.json();
        renderAnalyzeResult(data);
        showToast('วิเคราะห์และบันทึกข้อมูลสำเร็จ!');
        analyzeInput.value = '';
        
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        analyzeLoading.classList.add('hidden');
    }
});

function renderAnalyzeResult(data) {
    analyzeResult.classList.remove('hidden');
    
    // Top Banner Section
    let html = `
        <div class="glass-card" style="border-left: 4px solid var(--primary);">
            <h3 style="display:flex; align-items:center; gap:0.5rem">
                <i class="fa-brands fa-youtube" style="color: var(--primary)"></i> 
                📺 กำลังวิเคราะห์คลิป: <span style="color:white">${data.video_info.title}</span>
            </h3>
            <p style="margin-top:0.3rem">จากช่อง: <strong>${data.video_info.channel}</strong></p>
        </div>
        
        <!-- 3 Metric Cards -->
        <div class="dashboard-grid">
            <div class="metric-box">
                <h4>💬 จำนวนคอมเมนต์</h4>
                <div class="value">${formatNumber(data.video_info.comment_count)}</div>
            </div>
            <div class="metric-box">
                <h4>👍 ยอดไลก์สูงสุด</h4>
                <div class="value">${formatNumber(data.video_info.top_likes)}</div>
            </div>
            <div class="metric-box">
                <h4>🎭 อารมณ์ส่วนใหญ่</h4>
                <div class="value" style="color: var(--primary)">${data.video_info.top_sentiment}</div>
            </div>
        </div>
    `;

    // AI Executive Summary Card
    const ai = data.ai_summary || {};
    html += `<div class="glass-card"><h3 style="margin-bottom: 1.5rem">⚡ AI Executive Summary</h3>`;
    
    if (ai.error) {
        html += `
            <div style="background: rgba(239, 68, 68, 0.15); border-left: 4px solid var(--danger); padding: 1rem; border-radius: 8px; color: #fca5a5;">
                <strong>⚠️ เกิดข้อผิดพลาดในการสรุป:</strong> ${ai.error}
            </div>
        `;
    } else {
        html += `
            <div class="two-cols">
                <div>${renderExpanderList('🟢 สิ่งที่คนชอบ', ai.positive, '✨')}</div>
                <div>${renderExpanderList('🔴 ปัญหา/ดราม่า', ai.negative, '⚠️')}</div>
            </div>
            <div class="two-cols" style="margin-top: 1rem">
                <div>${renderExpanderList('🤡 แซว/ประชดประชัน', ai.sarcasm, '🤡')}</div>
                <div>${renderExpanderList('💡 สิ่งที่คนเรียกร้อง', ai.recommendation, '📌')}</div>
            </div>
        `;
    }
    html += `</div>`;

    // Timestamp Heatmap & Vision AI Section
    const peakCommentsList = data.peak_comments || [];
    const allTsCommentsList = data.all_ts_comments || [];
    
    let peakCommentsExpander = '';
    if (peakCommentsList.length > 0) {
        let commentsText = peakCommentsList.map(c => `<li style="margin-bottom:0.4rem;">${c}</li>`).join('');
        peakCommentsExpander = `
            <div class="expander" style="margin-top:1rem;">
                <div class="expander-header">
                    <span>💬 ดูคอมเมนต์ที่พูดถึงนาทีที่ ${data.peak_label} (${peakCommentsList.length})</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </div>
                <div class="expander-content">
                    <ul style="padding-left: 1.2rem; color: var(--text-muted); max-height: 200px; overflow-y: auto;">
                        ${commentsText}
                    </ul>
                </div>
            </div>
        `;
    }

    let allTsExpander = '';
    if (allTsCommentsList.length > 0) {
        let tsText = allTsCommentsList.map(c => `<li style="margin-bottom:0.4rem;">${c}</li>`).join('');
        allTsExpander = `
            <div class="expander" style="margin-top:0.5rem;">
                <div class="expander-header">
                    <span>⏱️ ดูคอมเมนต์ที่ระบุเวลาทั้งหมด (${allTsCommentsList.length})</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </div>
                <div class="expander-content">
                    <ul style="padding-left: 1.2rem; color: var(--text-muted); max-height: 200px; overflow-y: auto;">
                        ${tsText}
                    </ul>
                </div>
            </div>
        `;
    }

    html += `
        <div class="two-cols">
            <!-- Timestamp Heatmap -->
            <div class="glass-card">
                <h3 style="margin-bottom: 0.5rem">⏱️ Timestamp Heatmap</h3>
                <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom: 1.5rem">กราฟแสดงช่วงเวลาที่มีการคอมเมนต์ถึงมากที่สุด</p>
                <div style="position: relative; height: 280px;">
                    <canvas id="heatmapCanvas"></canvas>
                </div>
            </div>
            
            <!-- Multimodal Vision Analysis -->
            <div class="glass-card">
                <h3 style="margin-bottom: 0.5rem">👁️‍🗨️ Multimodal Vision Analysis</h3>
                <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom: 1rem">
                    <strong>ช็อตเด็ดที่สุดของคลิป:</strong> นาทีที่ <span style="background:rgba(239, 68, 68, 0.2); color:#fca5a5; padding:0.1rem 0.5rem; border-radius:4px;">${data.peak_label}</span>
                </p>
                ${data.frame_base64 ? `<img src="data:image/jpeg;base64,${data.frame_base64}" style="width:100%; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.4);">` : '<p style="color:var(--text-muted)">ไม่มีภาพเฟรม</p>'}
                ${data.highlight_summary ? `
                    <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid var(--success); padding: 1rem; border-radius: 6px; margin-bottom:1rem;">
                        <strong>🤖 AI Insight:</strong> ${data.highlight_summary}
                    </div>
                ` : ''}
                ${peakCommentsExpander}
                ${allTsExpander}
            </div>
        </div>
    `;

    // Sentiment Doughnut Chart & Word Cloud
    html += `
        <div class="two-cols">
            <div class="glass-card">
                <h3 style="margin-bottom: 1.5rem">📊 สัดส่วนอารมณ์ (Sentiment Ratio)</h3>
                <div style="position: relative; height: 280px; display:flex; justify-content:center;">
                    <canvas id="sentimentCanvas"></canvas>
                </div>
            </div>
            <div class="glass-card">
                <h3 style="margin-bottom: 1.5rem">☁️ คำที่พบบ่อย (Word Cloud)</h3>
                ${data.wordcloud_base64 ? `<img src="data:image/png;base64,${data.wordcloud_base64}" style="width:100%; border-radius: 8px;">` : '<p style="color:var(--text-muted)">ไม่สามารถสร้าง Word Cloud ได้</p>'}
            </div>
        </div>
    `;

    // All Comments Table Section
    const tableData = data.comments_table || [];
    let tableRows = '';
    tableData.forEach((c, idx) => {
        tableRows += `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 0.8rem 1rem; color: var(--text-muted); width: 60px;">${idx + 1}</td>
                <td style="padding: 0.8rem 1rem; word-break: break-word;">${c.text}</td>
                <td style="padding: 0.8rem 1rem; text-align: right; font-weight: 600; color: var(--primary); width: 100px;">👍 ${formatNumber(c.likes)}</td>
            </tr>
        `;
    });

    html += `
        <div class="glass-card">
            <h3 style="margin-bottom: 1.5rem">📋 ข้อมูลความคิดเห็นทั้งหมด (${tableData.length} ข้อความ)</h3>
            <div style="max-height: 350px; overflow-y: auto; border: 1px solid var(--card-border); border-radius: 8px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.95rem;">
                    <thead>
                        <tr style="background: rgba(255,255,255,0.08); position: sticky; top: 0; backdrop-filter: blur(8px);">
                            <th style="padding: 0.8rem 1rem; color: var(--text-muted);">#</th>
                            <th style="padding: 0.8rem 1rem; color: var(--text-muted);">ความคิดเห็น</th>
                            <th style="padding: 0.8rem 1rem; color: var(--text-muted); text-align: right;">ยอดไลก์</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    analyzeResult.innerHTML = html;
    attachExpanderEvents();

    // Render Charts via Chart.js
    renderHeatmapChart(data.timestamp_heatmap || []);
    renderSentimentChart(data.sentiment || {});
}

function renderHeatmapChart(heatmapData) {
    const ctx = document.getElementById('heatmapCanvas');
    if (!ctx) return;
    if (activeHeatmapChart) activeHeatmapChart.destroy();

    const labels = heatmapData.map(h => h.label);
    const counts = heatmapData.map(h => h.count);

    activeHeatmapChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'จำนวนคอมเมนต์',
                data: counts,
                backgroundColor: '#ef4444',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

function renderSentimentChart(sentimentData) {
    const ctx = document.getElementById('sentimentCanvas');
    if (!ctx) return;
    if (activeSentimentChart) activeSentimentChart.destroy();

    const pos = sentimentData.Positive || 0;
    const neg = sentimentData.Negative || 0;
    const neu = sentimentData.Neutral || 0;

    activeSentimentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['บวก (Positive)', 'ลบ (Negative)', 'ทั่วไป (Neutral)'],
            datasets: [{
                data: [pos, neg, neu],
                backgroundColor: ['#10b981', '#ef4444', '#94a3b8'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#f8fafc', font: { family: 'Prompt' } }
                }
            },
            cutout: '65%'
        }
    });
}

// =====================================
// History Page
// =====================================
async function loadHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = '<div class="spinner" style="margin: 2rem auto;"></div>';
    
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        
        document.getElementById('history-count').innerText = `📊 จำนวนรายงานที่บันทึกไว้: ${data.length} คลิป`;
        
        if (data.length === 0) {
            list.innerHTML = '<div class="glass-card"><p>ยังไม่มีข้อมูลในระบบ กรุณาไปที่หน้าวิเคราะห์คลิปใหม่เพื่อเพิ่มข้อมูลครับ</p></div>';
            return;
        }

        let html = '';
        data.forEach(item => {
            const match = item.video_url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/);
            const v_id = match ? match[1] : '';
            const thumbUrl = v_id ? `https://img.youtube.com/vi/${v_id}/hqdefault.jpg` : 'https://via.placeholder.com/250x140?text=No+Image';
            
            const title = item.video_title || `รายการวิเคราะห์ ID: ${item.id}`;
            const channel = item.channel_name || 'ไม่ทราบช่อง';
            
            html += `
                <div class="glass-card history-card" id="record-${item.id}">
                    <img src="${thumbUrl}" alt="Thumbnail" class="history-img">
                    <div class="history-info">
                        <label style="color:var(--text-muted); font-size:0.9rem; display:block; margin-bottom:0.2rem">📝 ชื่อข้อมูลวิเคราะห์ (แก้ไขได้)</label>
                        <input type="text" id="title-${item.id}" value="${title}">
                        <p style="margin-bottom: 0.5rem"><strong>📺 ช่อง:</strong> <span style="background: rgba(255,255,255,0.1); padding:0.1rem 0.5rem; border-radius:4px;">${channel}</span></p>
                        <p style="font-size: 0.9rem; color:var(--text-muted); margin-bottom: 0.5rem"><i class="fa-solid fa-link"></i> ${item.video_url}</p>
                        <p>💬 คอมเมนต์ทั้งหมด: <strong>${formatNumber(item.total_comments)}</strong> | ⏱️ จุดพีค: <strong>${item.peak_timestamp}</strong></p>
                        
                        <div style="display:flex; gap: 0.5rem; margin-top: 1rem">
                            <span class="badge positive">บวก: ${(item.positive_pct||0).toFixed(1)}%</span>
                            <span class="badge negative">ลบ: ${(item.negative_pct||0).toFixed(1)}%</span>
                            <span class="badge neutral">ทั่วไป: ${(item.neutral_pct||0).toFixed(1)}%</span>
                        </div>
                    </div>
                    <div class="history-actions">
                        <button class="btn-secondary" onclick="updateTitle(${item.id})">
                            <i class="fa-solid fa-floppy-disk"></i> บันทึกชื่อ
                        </button>
                        <button class="btn-danger" onclick="deleteRecord(${item.id})">
                            <i class="fa-solid fa-trash"></i> ลบข้อมูล
                        </button>
                    </div>
                </div>
            `;
        });
        
        list.innerHTML = html;
        
    } catch (e) {
        list.innerHTML = `<div class="glass-card" style="color:var(--danger)">Error loading history: ${e.message}</div>`;
    }
}

window.updateTitle = async (id) => {
    const newTitle = document.getElementById(`title-${id}`).value;
    try {
        const res = await fetch(`/api/history/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_title: newTitle })
        });
        if (res.ok) {
            showToast('อัปเดตชื่อสำเร็จ!');
        } else {
            showToast('อัปเดตชื่อไม่สำเร็จ', 'error');
        }
    } catch(e) {
        showToast(e.message, 'error');
    }
};

window.deleteRecord = async (id) => {
    if (!confirm('ยืนยันการลบข้อมูลนี้หรือไม่?')) return;
    try {
        const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
        if (res.ok) {
            document.getElementById(`record-${id}`).remove();
            showToast('ลบข้อมูลสำเร็จ');
            const currentCountStr = document.getElementById('history-count').innerText;
            const match = currentCountStr.match(/\d+/);
            if(match) {
                const count = parseInt(match[0]) - 1;
                document.getElementById('history-count').innerText = `📊 จำนวนรายงานที่บันทึกไว้: ${count} คลิป`;
            }
        } else {
            showToast('ลบข้อมูลไม่สำเร็จ', 'error');
        }
    } catch(e) {
        showToast(e.message, 'error');
    }
};

// =====================================
// Compare Page
// =====================================
async function loadCompareOptions() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const selectA = document.getElementById('compare-select-a');
        const selectB = document.getElementById('compare-select-b');
        
        let optionsHtml = '';
        data.forEach(item => {
            const title = item.video_title || `คลิป ID: ${item.id}`;
            optionsHtml += `<option value="${item.id}">${item.id} - ${title}</option>`;
        });
        
        selectA.innerHTML = optionsHtml;
        selectB.innerHTML = optionsHtml;
        
        if(data.length >= 2) {
            selectB.selectedIndex = 1;
        }
    } catch(e) {
        console.error("Failed to load options", e);
    }
}

document.getElementById('compare-btn').addEventListener('click', async () => {
    const idA = document.getElementById('compare-select-a').value;
    const idB = document.getElementById('compare-select-b').value;
    
    if (idA === idB) {
        showToast('กรุณาเลือกคลิปที่ไม่ซ้ำกัน', 'error');
        return;
    }
    
    document.getElementById('compare-result').classList.add('hidden');
    document.getElementById('compare-loading').classList.remove('hidden');
    
    try {
        const res = await fetch('/api/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_a: parseInt(idA), id_b: parseInt(idB) })
        });
        
        if (!res.ok) throw new Error('การประมวลผลล้มเหลว');
        const data = await res.json();
        
        renderCompareResult(data);
    } catch(e) {
        showToast(e.message, 'error');
    } finally {
        document.getElementById('compare-loading').classList.add('hidden');
    }
});

function renderCompareResult(resData) {
    const dataA = resData.data_a;
    const dataB = resData.data_b;
    const resultDiv = document.getElementById('compare-result');
    
    resultDiv.classList.remove('hidden');
    
    const getThumb = (url) => {
        const match = url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/);
        const v_id = match ? match[1] : '';
        return v_id ? `https://img.youtube.com/vi/${v_id}/hqdefault.jpg` : '';
    };

    let diffA = dataA.total_comments - dataB.total_comments;
    let diffB = dataB.total_comments - dataA.total_comments;
    
    const renderDelta = (diff) => {
        if (diff > 0) return `<span style="color:var(--success); font-size:0.9rem">▲ ${formatNumber(diff)}</span>`;
        if (diff < 0) return `<span style="color:var(--danger); font-size:0.9rem">▼ ${formatNumber(Math.abs(diff))}</span>`;
        return `<span style="color:var(--text-muted); font-size:0.9rem">-</span>`;
    };

    let html = `
        <div class="glass-card" style="margin-top: 2rem;">
            <h3 style="margin-bottom: 1.5rem">📈 1. เปรียบเทียบสถิติพื้นฐาน</h3>
            <div class="two-cols">
                <div>
                    <h4 style="color: var(--primary); margin-bottom: 1rem;">🔴 คลิป A</h4>
                    <img src="${getThumb(dataA.video_url)}" style="width:100%; border-radius:8px; margin-bottom:1rem">
                    <p style="font-weight:600; margin-bottom: 0.5rem">🎬 ${dataA.video_title || 'ไม่มีชื่อคลิป'}</p>
                    <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; margin-bottom:1rem">
                        <p style="color:var(--text-muted); font-size:0.9rem">คอมเมนต์ทั้งหมด</p>
                        <p style="font-size:1.5rem; font-weight:600">${formatNumber(dataA.total_comments)} ${renderDelta(diffA)}</p>
                    </div>
                </div>
                <div>
                    <h4 style="color: var(--info); margin-bottom: 1rem;">🔵 คลิป B</h4>
                    <img src="${getThumb(dataB.video_url)}" style="width:100%; border-radius:8px; margin-bottom:1rem">
                    <p style="font-weight:600; margin-bottom: 0.5rem">🎬 ${dataB.video_title || 'ไม่มีชื่อคลิป'}</p>
                    <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; margin-bottom:1rem">
                        <p style="color:var(--text-muted); font-size:0.9rem">คอมเมนต์ทั้งหมด</p>
                        <p style="font-size:1.5rem; font-weight:600">${formatNumber(dataB.total_comments)} ${renderDelta(diffB)}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="glass-card" style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid var(--success);">
            <h3>🤖 2. บทสรุปเปรียบเทียบจาก AI (Executive Conclusion)</h3>
            <p style="margin-top: 1rem; line-height: 1.6">${resData.ai_conclusion}</p>
        </div>
        
        <div class="glass-card">
            <h3 style="margin-bottom: 1.5rem">📝 3. เปรียบเทียบ Insight โดยละเอียด (หมัดต่อหมัด)</h3>
            <div class="two-cols">
                <div>
                    <h4 style="color: var(--primary); margin-bottom: 1rem;">🔴 คลิป A Insight</h4>
                    ${renderAiData(dataA.ai_summary)}
                </div>
                <div>
                    <h4 style="color: var(--info); margin-bottom: 1rem;">🔵 คลิป B Insight</h4>
                    ${renderAiData(dataB.ai_summary)}
                </div>
            </div>
        </div>
    `;
    
    resultDiv.innerHTML = html;
    attachExpanderEvents();
}

function renderAiData(jsonString) {
    if(!jsonString) return '<p>ไม่มีข้อมูล AI</p>';
    try {
        const ai = JSON.parse(jsonString);
        if (ai.error) return `<p style="color:var(--danger)">Error: ${ai.error}</p>`;
        let html = renderExpanderList('🟢 สิ่งที่คนชอบ', ai.positive, '✨');
        html += renderExpanderList('🔴 ปัญหา/ดราม่า', ai.negative, '⚠️');
        html += renderExpanderList('🤡 แซว/ประชดประชัน', ai.sarcasm, '🤡');
        html += renderExpanderList('💡 สิ่งที่คนเรียกร้อง', ai.recommendation, '📌');
        return html;
    } catch(e) {
        return '<p>เกิดข้อผิดพลาดในการอ่านข้อมูล AI</p>';
    }
}




// Global Toast Notification Helper
window.showToast = function(title, message, type = 'success', duration = 3500) {
  let container = document.getElementById('colony-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'colony-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `colony-toast toast-${type}`;

  const iconMap = {
    success: '✓',
    error: '✗',
    info: 'ℹ',
    warning: '⚠'
  };

  toast.innerHTML = `
    <div class="toast-icon-wrap">${iconMap[type] || '✓'}</div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-msg">${message}</div>` : ''}
    </div>
    <button class="toast-close-btn">✕</button>
  `;

  const closeBtn = toast.querySelector('.toast-close-btn');
  const dismiss = () => {
    toast.classList.add('toast-leaving');
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 250);
  };

  closeBtn.addEventListener('click', dismiss);
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }
};

/**
 * Ant Colony AI - 3D Isometric Hive Canvas, Dynamic Skill Matrix, AI Leaderboard, Ishchi muhit & CEO Executive Briefing
 */

// Helper to sanitize long model names
function cleanModelLabel(name) {
  if (!name) return 'В режиме ожидания';
  let str = String(name).trim();
  if (str.includes('/')) str = str.split('/').pop();
  if (str.includes(':')) str = str.split(':')[0];
  str = str.replace(/-nano-omni-30b-a3b-reasoning/gi, ' Nano')
           .replace(/-flash-lite/gi, ' Lite')
           .replace(/-flash/gi, ' Flash')
           .replace(/-lightning/gi, '')
           .replace(/nemotron-3\.5/gi, 'Nemotron 3.5')
           .replace(/deepseek-v4/gi, 'DeepSeek V4')
           .replace(/gemini-2\.5/gi, 'Gemini 2.5');
  if (str.length > 22) str = str.slice(0, 20) + '..';
  return str;
}

// --- 1. Isometric Canvas Engine ---

class IsometricHiveCanvas {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.width = 0;
    this.height = 0;
    this.time = 0;
    this.activeStation = 'pm';

    // Professional Russian Role Titles
    this.stations = [
      { id: 'pm', name: 'Центральное управление (PM)', sub: 'DeepSeek V4 Flash', roleId: 'pm_orchestrator', x: 0, y: 0, color: '#8b5cf6', active: true, action: '' },
      { id: 'coder', name: 'Инженер-разработчик', sub: 'DeepSeek V4 Flash', roleId: 'frontend_architect', x: -230, y: -80, color: '#6366f1', active: false, action: '' },
      { id: 'tester', name: 'Инженер тестирования (QA)', sub: 'Nemotron 3.5', roleId: 'qa_test_automation', x: -130, y: 110, color: '#06b6d4', active: false, action: '' },
      { id: 'researcher', name: 'Аналитик данных', sub: 'Gemini 2.5 Flash', roleId: 'data_engineer', x: 230, y: -80, color: '#10b981', active: false, action: '' },
      { id: 'designer', name: 'Дизайнер UI/UX', sub: 'DeepSeek V4 Flash', roleId: 'ui_ux_designer', x: -250, y: 35, color: '#ec4899', active: false, action: '' },
      { id: 'deployer', name: 'Инженер DevOps', sub: 'Hy3 Faster', roleId: 'devops_deployer', x: 130, y: 110, color: '#f97316', active: false, action: '' },
      { id: 'monitor', name: 'Аудит безопасности', sub: 'Nemotron 3.5', roleId: 'security_auditor', x: 250, y: 35, color: '#f59e0b', active: false, action: '' }
    ];

    this.drones = [];
    this.initDrones(18);
    this.pulses = [];

    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.animate();
  }

  resize() {
    const parent = this.canvas.parentElement;
    if (!parent) return;
    this.width = parent.clientWidth;
    this.height = parent.clientHeight;
    this.canvas.width = this.width * window.devicePixelRatio;
    this.canvas.height = this.height * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }

  initDrones(count) {
    this.drones = [];
    for (let i = 0; i < count; i++) {
      const targetIdx = Math.floor(Math.random() * (this.stations.length - 1)) + 1;
      this.drones.push({
        from: 0,
        to: targetIdx,
        progress: Math.random(),
        speed: 0.003 + Math.random() * 0.004,
        size: 7 + Math.random() * 3,
        color: this.stations[targetIdx].color,
        hasPacket: Math.random() > 0.3
      });
    }
  }

  updateRoles(rolesList) {
    if (!rolesList || !Array.isArray(rolesList)) return;
    const roleMap = {};
    rolesList.forEach(r => {
      roleMap[r.id] = r;
    });

    this.stations.forEach(st => {
      if (st.roleId && roleMap[st.roleId]) {
        const r = roleMap[st.roleId];
        st.sub = r.model_name || r.assigned_model || st.sub;
      }
    });
  }

  setActiveStation(stationId, actionLabel = '', modelName = '') {
    this.activeStation = stationId;
    this.stations.forEach(st => {
      st.active = (st.id === stationId || st.id === 'pm');
      if (st.id === stationId) {
        if (actionLabel) st.action = actionLabel;
        if (modelName) st.sub = modelName;
      } else if (st.id !== 'pm') {
        st.action = '';
      }
    });

    const target = this.stations.find(s => s.id === stationId);
    if (target && target.id !== 'pm') {
      for (let i = 0; i < 6; i++) {
        this.pulses.push({
          targetX: target.x,
          targetY: target.y,
          progress: i * 0.16,
          color: target.color
        });
      }
    }
  }

  updateStationModel(stationId, modelName, actionText = '') {
    const target = this.stations.find(s => s.id === stationId);
    if (target) {
      if (modelName) target.sub = modelName;
      if (actionText !== undefined) target.action = actionText;
    }
  }

  drawIsoHexagon(cx, cy, radius, height, color, glow = false) {
    const ctx = this.ctx;
    const angles = [0, 60, 120, 180, 240, 300].map(deg => (deg * Math.PI) / 180);
    const isLight = document.body.classList.contains('light-theme');

    // 1. Shadow
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const px = cx + radius * 1.05 * Math.cos(angles[i]);
      const py = cy + 14 + (radius * 0.52 * Math.sin(angles[i]));
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(0, 0, 0, 0.45)';
    ctx.fill();

    // 2. 3D Side Walls
    for (let i = 0; i < 6; i++) {
      const next = (i + 1) % 6;
      const x1 = cx + radius * Math.cos(angles[i]);
      const y1 = cy + (radius * 0.5 * Math.sin(angles[i]));
      const x2 = cx + radius * Math.cos(angles[next]);
      const y2 = cy + (radius * 0.5 * Math.sin(angles[next]));

      if (angles[i] >= 0 && angles[i] <= Math.PI) {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.lineTo(x2, y2 + height);
        ctx.lineTo(x1, y1 + height);
        ctx.closePath();
        ctx.fillStyle = isLight ? (i === 1 ? '#e2e8f0' : '#cbd5e1') : (i === 1 ? '#0b1324' : '#080e1b');
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // 3. Top Hexagon Face
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const px = cx + radius * Math.cos(angles[i]);
      const py = cy + (radius * 0.5 * Math.sin(angles[i]));
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();

    const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, radius);
    if (isLight) {
      grad.addColorStop(0, glow ? color : '#f8fafc');
      grad.addColorStop(1, '#ffffff');
    } else {
      grad.addColorStop(0, glow ? color : '#1e293b');
      grad.addColorStop(1, '#0f172a');
    }
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.strokeStyle = color;
    ctx.lineWidth = glow ? 2.5 : 1.2;
    if (glow) {
      ctx.shadowColor = color;
      ctx.shadowBlur = 15;
    }
    ctx.stroke();
    ctx.shadowBlur = 0;
  }

  drawStation(station, cx, cy) {
    const ctx = this.ctx;
    const sx = cx + station.x;
    const sy = cy + station.y;
    const isPM = station.id === 'pm';
    const radius = isPM ? 52 : 36;
    const height = isPM ? 16 : 10;
    const isLight = document.body.classList.contains('light-theme');

    this.drawIsoHexagon(sx, sy, radius, height, station.color, station.active);

    if (station.active) {
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(sx, sy - 8, radius * 0.8, radius * 0.4, this.time * 0.02, 0, Math.PI * 2);
      ctx.strokeStyle = station.color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 6]);
      ctx.stroke();
      ctx.restore();
    }

    // Node beacon
    ctx.beginPath();
    ctx.arc(sx, sy - 6, isPM ? 10 : 7, 0, Math.PI * 2);
    ctx.fillStyle = station.color;
    ctx.shadowColor = station.color;
    ctx.shadowBlur = station.active ? 20 : 8;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Station Name (Noun role title)
    ctx.font = isPM ? '700 12px "Plus Jakarta Sans"' : '600 10.5px "Plus Jakarta Sans"';
    ctx.fillStyle = isLight ? '#0f172a' : '#ffffff';
    ctx.textAlign = 'center';
    ctx.fillText(station.name, sx, sy + height + 16);

    // Stansiya tavsifi: Model nomi va haqiqiy holati (Faol yoki Kutish rejimida)
    const cleanModel = cleanModelLabel(station.sub);
    ctx.font = '500 9.5px "JetBrains Mono"';
    if (station.active && !isPM) {
      ctx.fillStyle = station.color;
      ctx.fillText(`Faol • ${cleanModel}`, sx, sy + height + 28);
    } else if (isPM) {
      ctx.fillStyle = station.color;
      ctx.fillText(cleanModel, sx, sy + height + 28);
    } else {
      ctx.fillStyle = isLight ? '#94a3b8' : '#64748b';
      ctx.fillText(`${cleanModel} • В режиме ожидания`, sx, sy + height + 28);
    }

    // Live Floating Action HUD Badge (Only when active)
    if (station.active && station.action) {
      const pillY = sy - radius - 16;
      ctx.font = '600 10px "Plus Jakarta Sans"';
      const labelText = station.action.length > 24 ? station.action.slice(0, 22) + '..' : station.action;
      const textWidth = ctx.measureText(labelText).width;
      const pillW = textWidth + 18;
      const pillH = 20;

      ctx.save();
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(sx - pillW / 2, pillY - pillH / 2, pillW, pillH, 10);
      } else {
        ctx.rect(sx - pillW / 2, pillY - pillH / 2, pillW, pillH);
      }
      ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.95)' : 'rgba(15, 23, 42, 0.92)';
      ctx.strokeStyle = station.color;
      ctx.lineWidth = 1.2;
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = station.color;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, sx, pillY);
      ctx.restore();
    }
  }

  drawConduits(cx, cy) {
    const ctx = this.ctx;
    const pm = this.stations[0];
    const pmX = cx + pm.x;
    const pmY = cy + pm.y;

    for (let i = 1; i < this.stations.length; i++) {
      const st = this.stations[i];
      const stX = cx + st.x;
      const stY = cy + st.y;

      ctx.beginPath();
      ctx.moveTo(pmX, pmY);
      ctx.lineTo(stX, stY);
      ctx.strokeStyle = st.active ? st.color : 'rgba(99, 102, 241, 0.18)';
      ctx.lineWidth = st.active ? 2 : 1;
      ctx.setLineDash(st.active ? [4, 4] : [2, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  updateAndDrawPulses(cx, cy) {
    const ctx = this.ctx;
    const pm = this.stations[0];
    const pmX = cx + pm.x;
    const pmY = cy + pm.y;

    for (let i = this.pulses.length - 1; i >= 0; i--) {
      const p = this.pulses[i];
      p.progress += 0.02;
      if (p.progress > 1) {
        this.pulses.splice(i, 1);
        continue;
      }

      const px = pmX + p.targetX * p.progress;
      const py = pmY + p.targetY * p.progress;

      ctx.beginPath();
      ctx.arc(px, py, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  updateAndDrawDrones(cx, cy) {
    const ctx = this.ctx;

    this.drones.forEach(drone => {
      drone.progress += drone.speed;
      if (drone.progress > 1) {
        drone.progress = 0;
        const activeStIdx = this.stations.findIndex(s => s.id === this.activeStation && s.id !== 'pm');
        if (activeStIdx > 0 && Math.random() < 0.7) {
          drone.to = activeStIdx;
        } else {
          drone.to = Math.floor(Math.random() * (this.stations.length - 1)) + 1;
        }
        drone.color = this.stations[drone.to].color;
      }

      const sFrom = this.stations[drone.from];
      const sTo = this.stations[drone.to];
      const dx = (cx + sFrom.x) + ((cx + sTo.x) - (cx + sFrom.x)) * drone.progress;
      const dy = (cy + sFrom.y) + ((cy + sTo.y) - (cy + sFrom.y)) * drone.progress;

      const bob = Math.sin(this.time * 0.08 + drone.size) * 3;

      ctx.beginPath();
      ctx.ellipse(dx, dy + 8, drone.size * 0.7, drone.size * 0.35, 0, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(dx, dy + bob, drone.size * 0.5, 0, Math.PI * 2);
      ctx.fillStyle = document.body.classList.contains('light-theme') ? '#ffffff' : '#0f172a';
      ctx.strokeStyle = drone.color;
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(dx, dy + bob - 1, 2, 0, Math.PI * 2);
      ctx.fillStyle = drone.color;
      ctx.shadowColor = drone.color;
      ctx.shadowBlur = 6;
      ctx.fill();
      ctx.shadowBlur = 0;

      if (drone.hasPacket) {
        ctx.beginPath();
        ctx.rect(dx - 2, dy + bob + 3, 4, 3);
        ctx.fillStyle = '#38bdf8';
        ctx.fill();
      }
    });
  }

  animate() {
    this.time++;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    const cx = this.width / 2;
    const cy = this.height / 2 - 15;

    this.drawConduits(cx, cy);
    this.updateAndDrawPulses(cx, cy);
    this.updateAndDrawDrones(cx, cy);
    this.stations.forEach(st => this.drawStation(st, cx, cy));

    requestAnimationFrame(() => this.animate());
  }
}

// --- 2. Main App Controller ---

// Live Workspace — real-time fayl daraxti va terminal oqimi boshqaruvchisi
class LiveWorkspaceController {
  constructor() {
    this.treeRoot = document.getElementById('lw-tree-scroll');
    this.termRoot = document.getElementById('lw-term-scroll');
    this.metaTree = document.getElementById('lw-tree-meta');
    this.metaTerm = document.getElementById('lw-term-meta');
    this.liveDot = document.getElementById('lw-live-dot');
    this.liveLabel = document.getElementById('lw-live-label');
    // Fayl yo'liga qarab DOM tugunini topish uchun.
    this.fileNodes = new Map();
    this.termBlocks = new Map(); // exec_id → {block, linesEl, statusEl}
    this.termCount = 0;
    this.autoScrollTerm = true;
    if (this.termRoot) {
      this.termRoot.addEventListener('scroll', () => {
        const nearBottom = this.termRoot.scrollHeight - this.termRoot.scrollTop - this.termRoot.clientHeight < 40;
        this.autoScrollTerm = nearBottom;
      });
    }
  }

  setLive(live, label) {
    if (this.liveDot) this.liveDot.classList.toggle('live', !!live);
    if (this.liveLabel && label) this.liveLabel.textContent = label;
  }

  esc(v) {
    if (v === null || v === undefined) return '';
    return String(v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  fmtSize(bytes) {
    if (!bytes || bytes < 1024) return `${bytes || 0} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async refreshTree() {
    if (!this.treeRoot) return;
    try {
      const res = await fetch('/api/workspace/tree');
      const data = await res.json();
      this.renderTree(data);
    } catch (err) {
      this.treeRoot.innerHTML = `<div class="lw-placeholder">Ошибка загрузки: ${this.esc(err.message)}</div>`;
    }
  }

  renderTree(data) {
    this.fileNodes.clear();
    const parts = [];
    const roots = [
      { label: 'Активный проект', tree: data.active_project },
      { label: 'Workspace', tree: data.workspace },
    ];
    let totalFiles = 0;
    for (const r of roots) {
      const t = r.tree;
      if (!t) continue;
      parts.push(`<div class="lw-root-label">${this.esc(r.label)} — <span title="${this.esc(t.path)}">${this.esc(t.name)}</span>${t.truncated ? ' (список усечён)' : ''}</div>`);
      if (!t.exists) {
        parts.push('<div class="lw-placeholder">Папка ещё не создана</div>');
        continue;
      }
      const rootKey = r.label === 'Активный проект' ? 'active' : 'workspace';
      parts.push(`<div class="lw-tree" data-scope="${rootKey}">${this.renderNodes(t.children || [], rootKey)}</div>`);
      totalFiles += this.countFiles(t.children || []);
    }
    this.treeRoot.innerHTML = parts.join('') || '<div class="lw-placeholder">Пустой проект</div>';
    if (this.metaTree) this.metaTree.textContent = `${totalFiles} файлов`;
    // DOM tugunlarni indekslash — jonli update uchun.
    this.treeRoot.querySelectorAll('[data-fpath]').forEach(el => {
      this.fileNodes.set(el.getAttribute('data-fpath'), el);
    });
  }

  countFiles(children) {
    let n = 0;
    for (const c of children) {
      if (c.type === 'file') n++;
      else if (c.children) n += this.countFiles(c.children);
    }
    return n;
  }

  renderNodes(nodes, scope) {
    const items = nodes.map(n => {
      const isDir = n.type === 'dir';
      const key = `${scope}::${n.path}`;
      const ico = isDir
        ? '<svg class="lw-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>'
        : '<svg class="lw-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
      const size = !isDir ? `<span class="lw-size">${this.fmtSize(n.size || 0)}</span>` : '';
      const inner = `<span class="lw-node ${isDir ? 'dir' : 'file'}" data-fpath="${this.esc(key)}">${ico}<span>${this.esc(n.name)}</span>${size}</span>`;
      const kids = isDir && n.children && n.children.length
        ? `<ul>${this.renderNodes(n.children, scope)}</ul>` : '';
      return `<li>${inner}${kids}</li>`;
    }).join('');
    return `<ul>${items}</ul>`;
  }

  // fs_change eventi kelganda daraxtni jonli yangilash.
  handleFsChange(ev) {
    const scope = 'active';
    const rel = (ev.filename || '').replace(/^\/+/, '');
    if (!rel) return;
    const key = `${scope}::${rel}`;
    let node = this.fileNodes.get(key);
    if (node) {
      const sizeEl = node.querySelector('.lw-size');
      if (sizeEl) sizeEl.textContent = this.fmtSize(ev.size_bytes || 0);
      node.classList.remove('pulse');
      // reflow trik — animatsiya qayta boshlanadi
      void node.offsetWidth;
      node.classList.add('pulse');
    } else {
      // Yangi fayl — daraxtga tugun qo'shamiz. Oddiyroq yo'l: to'liq refresh.
      this.refreshTree();
    }
  }

  handleTerminalStream(ev) {
    if (!this.termRoot) return;
    const placeholder = this.termRoot.querySelector('.lw-placeholder');
    if (placeholder) placeholder.remove();

    const eid = ev.exec_id || 'default';
    let entry = this.termBlocks.get(eid);

    if (ev.phase === 'start' || !entry) {
      const wrapper = document.createElement('div');
      wrapper.className = 'lw-term-block running';
      wrapper.innerHTML = `
        <div class="lw-term-cmd">${this.esc(ev.command || '(команда)')}${ev.cwd ? `<span class="lw-term-cwd">${this.esc(ev.cwd)}</span>` : ''}</div>
        <div class="lw-term-lines"></div>
        <div class="lw-term-status">выполняется…</div>`;
      this.termRoot.appendChild(wrapper);
      entry = {
        block: wrapper,
        linesEl: wrapper.querySelector('.lw-term-lines'),
        statusEl: wrapper.querySelector('.lw-term-status'),
      };
      this.termBlocks.set(eid, entry);
      this.termCount++;
      if (this.metaTree) this.metaTree.textContent = this.metaTree.textContent; // keep
      if (this.metaTerm) this.metaTerm.textContent = `${this.termCount} команд`;
      if (this.autoScrollTerm) this.termRoot.scrollTop = this.termRoot.scrollHeight;
      if (ev.phase === 'start') return;
    }

    if (ev.phase === 'line' || ev.phase === 'timeout' || ev.phase === 'error' || ev.phase === 'blocked') {
      const line = document.createElement('div');
      line.className = `lw-term-line ${ev.stream === 'stderr' ? 'stderr' : ''}`;
      line.textContent = ev.line || '';
      entry.linesEl.appendChild(line);
      if (this.autoScrollTerm) this.termRoot.scrollTop = this.termRoot.scrollHeight;
    }

    if (ev.phase === 'end') {
      entry.block.classList.remove('running');
      entry.block.classList.add(ev.success ? 'ok' : 'fail');
      entry.statusEl.className = `lw-term-status ${ev.success ? 'ok' : 'fail'}`;
      entry.statusEl.textContent = ev.success
        ? `✓ Готово · код ${ev.returncode} · ${ev.duration_ms} мс`
        : `✗ Ошибка · код ${ev.returncode} · ${ev.duration_ms} мс`;
    } else if (ev.phase === 'blocked') {
      entry.block.classList.remove('running');
      entry.block.classList.add('blocked');
      entry.statusEl.className = 'lw-term-status fail';
      entry.statusEl.textContent = '⚠ Заблокировано политикой безопасности';
    }
  }

  clearTerminal() {
    if (!this.termRoot) return;
    this.termRoot.innerHTML = '<div class="lw-placeholder">Терминал очищен. Ожидание новых команд…</div>';
    this.termBlocks.clear();
    this.termCount = 0;
    if (this.metaTerm) this.metaTerm.textContent = '0 команд';
  }
}

// Deploy controller — GitHub va Netlify uchun modal boshqaruvi.
class DeployController {
  constructor() {
    this.modal = document.getElementById('modal-deploy');
    this.projectSel = document.getElementById('dep-project-select');
    this.resultEl = document.getElementById('dep-result');
    this._bindTabs();
  }

  esc(v) {
    if (v === null || v === undefined) return '';
    return String(v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  _bindTabs() {
    const tabs = this.modal ? this.modal.querySelectorAll('.deploy-tab') : [];
    tabs.forEach(t => {
      t.addEventListener('click', () => {
        tabs.forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        const which = t.getAttribute('data-tab');
        this.modal.querySelectorAll('.deploy-tab-panel').forEach(p => {
          p.classList.toggle('hidden', p.getAttribute('data-panel') !== which);
        });
      });
    });
  }

  async open() {
    if (!this.modal) return;
    this.modal.classList.remove('hidden');
    this.resultEl.style.display = 'none';
    await this._loadProjects();
  }

  close() {
    if (this.modal) this.modal.classList.add('hidden');
  }

  async _loadProjects() {
    if (!this.projectSel) return;
    try {
      const res = await fetch('/api/deploy/projects');
      const data = await res.json();
      const projects = (data.projects || []).filter(p => p.has_files);
      if (!projects.length) {
        this.projectSel.innerHTML = '<option value="">Проектов пока нет — создайте один через PM</option>';
        return;
      }
      this.projectSel.innerHTML = projects.map(p =>
        `<option value="${this.esc(p.name)}">${this.esc(p.name)}${p.has_git ? ' · git' : ''}</option>`
      ).join('');
    } catch (err) {
      this.projectSel.innerHTML = `<option value="">Ошибка: ${this.esc(err.message)}</option>`;
    }
  }

  _showResult(ok, html) {
    this.resultEl.style.display = 'block';
    this.resultEl.className = `deploy-result ${ok ? 'ok' : 'err'}`;
    this.resultEl.innerHTML = html;
  }

  async runGitHub() {
    const project = this.projectSel.value;
    const token = document.getElementById('dep-gh-token').value.trim();
    const repo = document.getElementById('dep-gh-repo').value.trim();
    const desc = document.getElementById('dep-gh-desc').value.trim();
    const priv = document.getElementById('dep-gh-private').checked;
    if (!project) return this._showResult(false, 'Выберите проект');
    if (!token) return this._showResult(false, 'Введите GitHub Personal Access Token');
    if (!repo) return this._showResult(false, 'Введите имя репозитория');

    const btn = document.getElementById('btn-deploy-github');
    btn.disabled = true; btn.textContent = 'Пушим…';
    this._showResult(true, 'Создаём репозиторий и пушим…');

    try {
      const res = await fetch('/api/deploy/github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token, project_name: project, repo_name: repo,
          description: desc, private: priv,
        }),
      });
      const data = await res.json();
      if (data.success) {
        this._showResult(true,
          `✓ Готово!\n\n<a href="${this.esc(data.html_url)}" target="_blank">${this.esc(data.html_url)}</a>\n\nШагов: ${data.steps.length}`);
      } else {
        const details = (data.steps || []).map(s => `${s.ok ? '✓' : '✗'} ${s.step}${s.stderr ? ': ' + s.stderr.slice(0,140) : ''}`).join('\n');
        this._showResult(false, `Ошибка: ${this.esc(data.error || 'unknown')}\n\n${this.esc(details)}`);
      }
    } catch (err) {
      this._showResult(false, `Сетевая ошибка: ${this.esc(err.message)}`);
    } finally {
      btn.disabled = false; btn.textContent = 'Создать репо и push';
    }
  }

  async runNetlify() {
    const project = this.projectSel.value;
    const token = document.getElementById('dep-nf-token').value.trim();
    const name = document.getElementById('dep-nf-name').value.trim();
    if (!project) return this._showResult(false, 'Выберите проект');
    if (!token) return this._showResult(false, 'Введите Netlify PAT');

    const btn = document.getElementById('btn-deploy-netlify');
    btn.disabled = true; btn.textContent = 'Загружаем…';
    this._showResult(true, 'Упаковываем проект и деплоим…');

    try {
      const res = await fetch('/api/deploy/netlify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, project_name: project, site_name: name || null }),
      });
      const data = await res.json();
      if (data.success) {
        this._showResult(true,
          `✓ Развёрнут!\n\nСайт: <a href="${this.esc(data.site_url)}" target="_blank">${this.esc(data.site_url)}</a>\nАдмин-панель: <a href="${this.esc(data.admin_url)}" target="_blank">${this.esc(data.admin_url)}</a>\n\nФайлов: ${data.files_included}${data.files_skipped ? ` (пропущено: ${data.files_skipped})` : ''}\nРазмер архива: ${(data.zip_size_bytes/1024).toFixed(0)} KB`);
      } else {
        this._showResult(false, `Ошибка: ${this.esc(data.error || 'unknown')}`);
      }
    } catch (err) {
      this._showResult(false, `Сетевая ошибка: ${this.esc(err.message)}`);
    } finally {
      btn.disabled = false; btn.textContent = 'Deploy на Netlify';
    }
  }
}

class AntColonyApp {
  constructor() {
    if (typeof IsometricHive3D !== 'undefined') {
      this.canvas = new IsometricHive3D('hive-viewport', 'hive-canvas');
    } else {
      this.canvas = new IsometricHiveCanvas('hive-canvas');
    }
    this.initTheme();
    this.initUI();
    this.liveWorkspace = new LiveWorkspaceController();
    this.liveWorkspace.refreshTree();
    this.deploy = new DeployController();
    this.restoreChatHistory();
    this.checkAndReconnectActiveJob();
    this.fetchRealStats();
    this.loadRolesOnStartup();
    this.checkFirstRunSetup();
    this.setupIdleSwarmMonitor();
    this.activeLbCategory = 'all';
    
    // Auto-refresh real stats every 3 seconds
    setInterval(() => this.fetchRealStats(), 3000);

    // Auto-refresh models table if open
    setInterval(() => {
      const modal = document.getElementById('modal-models-hub');
      if (modal && !modal.classList.contains('hidden')) {
        this.renderModelsTable();
      }
    }, 4000);
  }

  initTheme() {
    const savedTheme = localStorage.getItem('ant_theme') || 'dark';
    if (savedTheme === 'light') {
      document.body.classList.remove('dark-theme');
      document.body.classList.add('light-theme');
      this.updateThemeUI(true);
    } else {
      document.body.classList.remove('light-theme');
      document.body.classList.add('dark-theme');
      this.updateThemeUI(false);
    }
  }

  toggleTheme() {
    const isLight = document.body.classList.contains('light-theme');
    if (isLight) {
      document.body.classList.remove('light-theme');
      document.body.classList.add('dark-theme');
      localStorage.setItem('ant_theme', 'dark');
      this.updateThemeUI(false);
    } else {
      document.body.classList.remove('dark-theme');
      document.body.classList.add('light-theme');
      localStorage.setItem('ant_theme', 'light');
      this.updateThemeUI(true);
    }
  }

  updateThemeUI(isLight) {
    const label = document.getElementById('theme-label-text');
    const darkIcon = document.querySelector('.theme-icon-dark');
    const lightIcon = document.querySelector('.theme-icon-light');

    if (label) label.textContent = isLight ? 'Dark mode' : 'Light mode';
    if (darkIcon && lightIcon) {
      if (isLight) {
        darkIcon.classList.add('hidden');
        lightIcon.classList.remove('hidden');
      } else {
        darkIcon.classList.remove('hidden');
        lightIcon.classList.add('hidden');
      }
    }
    if (this.canvas && typeof this.canvas.setTheme === 'function') {
      this.canvas.setTheme(isLight);
    }
  }

  initUI() {
    const on = (id, event, handler) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener(event, handler);
    };

    // Theme toggle
    on('btn-theme-toggle', 'click', () => this.toggleTheme());

    // Drawer toggles
    on('btn-pm-console-toggle', 'click', () => this.togglePMDrawer(true));
    on('btn-sidebar-pm', 'click', () => this.togglePMDrawer(true));
    on('btn-close-pm-drawer', 'click', () => this.togglePMDrawer(false));

    // Live Workspace drawer
    on('btn-open-live-workspace', 'click', () => this.toggleLiveWorkspace(true));
    on('btn-close-lw-drawer', 'click', () => this.toggleLiveWorkspace(false));
    on('btn-lw-refresh', 'click', () => this.liveWorkspace && this.liveWorkspace.refreshTree());
    on('btn-lw-clear-term', 'click', () => this.liveWorkspace && this.liveWorkspace.clearTerminal());

    // Deploy modal
    on('btn-open-deploy', 'click', () => this.deploy && this.deploy.open());
    on('btn-close-deploy', 'click', () => this.deploy && this.deploy.close());
    on('btn-deploy-github', 'click', () => this.deploy && this.deploy.runGitHub());
    on('btn-deploy-netlify', 'click', () => this.deploy && this.deploy.runNetlify());

    // FPS / quality badge — click cycles auto → high → medium → low → auto
    const fpsBadge = document.getElementById('fps-badge');
    if (fpsBadge) {
      let modes = ['auto', 'high', 'medium', 'low'];
      let idx = 0;
      fpsBadge.addEventListener('click', () => {
        idx = (idx + 1) % modes.length;
        const m = modes[idx];
        if (this.canvas && typeof this.canvas.setQualityMode === 'function') {
          this.canvas.setQualityMode(m);
        }
      });
      this._fpsBadgeTimer = setInterval(() => {
        if (!this.canvas || typeof this.canvas.getPerformanceStats !== 'function') return;
        const s = this.canvas.getPerformanceStats();
        const fEl = document.getElementById('fps-badge-fps');
        const mEl = document.getElementById('fps-badge-mode');
        if (fEl) fEl.textContent = s.fps || '–';
        if (mEl) {
          mEl.textContent = s.mode;
          mEl.style.color = s.mode === 'high' ? '#22c55e' : (s.mode === 'medium' ? '#f59e0b' : '#ef4444');
        }
      }, 800);
    }

    // Send task
    on('btn-pm-send-task', 'click', () => this.dispatchPMTask());
    // Quick chips
    const quickChips = document.getElementById('pm-quick-chips');
    if (quickChips) {
      quickChips.addEventListener('click', (e) => {
        const btn = e.target.closest('.quick-chip-btn');
        if (!btn) return;
        const taskText = btn.getAttribute('data-task');
        const input = document.getElementById('pm-task-input');
        if (input && taskText) {
          input.value = taskText;
          input.focus();
        }
      });
    }

    on('pm-task-input', 'keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.dispatchPMTask();
      }
    });

    // AI Leaderboard Modal
    on('btn-top-leaderboard', 'click', () => this.openLeaderboardModal());
    on('btn-sidebar-leaderboard', 'click', () => this.openLeaderboardModal());
    on('btn-close-leaderboard-modal', 'click', () => this.closeLeaderboardModal());

    // Filter tabs in Leaderboard
    const lbFilterContainer = document.getElementById('lb-filters-bar');
    if (lbFilterContainer) {
      lbFilterContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('.lb-filter-btn');
        if (!btn) return;
        lbFilterContainer.querySelectorAll('.lb-filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeLbCategory = btn.getAttribute('data-cat') || 'all';
        this.renderLeaderboardTable();
      });
    }

    // CEO Briefing Modal
    on('btn-top-open-ceo', 'click', () => this.openCEOBriefingModal());
    on('btn-sidebar-ceo-briefing', 'click', () => this.openCEOBriefingModal());
    on('btn-close-ceo-modal', 'click', () => this.closeCEOBriefingModal());
    on('btn-ceo-terminal-run', 'click', () => this.runCEOTerminalCommand());

    // Setup Wizard
    on('btn-top-setup', 'click', () => this.openSetupModal());
    on('btn-close-setup-modal', 'click', () => this.closeSetupModal());

    // Roles & Skill Matrix Modal
    on('btn-sidebar-roles', 'click', () => this.openRolesModal());
    on('btn-hive-open-roles', 'click', () => this.openRolesModal());
    on('btn-close-roles-modal', 'click', () => this.closeRolesModal());

    // Auto Monitoring Modal
    on('btn-sidebar-models', 'click', () => this.openModelsModal());
    on('btn-hive-ping-models', 'click', () => this.openModelsModal());
    on('btn-close-models-modal', 'click', () => this.closeModelsModal());

    // Workspace / Ishchi Muhit Modal
    on('btn-sidebar-desktop-projects', 'click', () => this.openDesktopProjectsModal());
    on('btn-close-workspace-modal', 'click', () => this.closeDesktopProjectsModal());
    
    on('btn-top-ping-all', 'click', () => this.pingAllModels());

    // Clear Chat History
    on('btn-clear-pm-feed', 'click', () => this.clearChatHistory());
  }

  saveChatHistory() {
    const feed = document.getElementById('pm-feed-list');
    if (!feed) return;
    try {
      localStorage.setItem('ant_chat_history', feed.innerHTML);
    } catch (e) {}
  }

  restoreChatHistory() {
    const feed = document.getElementById('pm-feed-list');
    if (!feed) return;
    const saved = localStorage.getItem('ant_chat_history');
    if (saved && saved.trim()) {
      feed.innerHTML = saved;
      const placeholder = document.getElementById('pm-empty-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      // Re-attach accordion click handlers to any saved thinking cards
      feed.querySelectorAll('.chat-thinking-card').forEach(card => {
        const header = card.querySelector('.thinking-header');
        if (header) {
          header.onclick = () => card.classList.toggle('collapsed');
        }
      });
    }
  }

  clearChatHistory() {
    localStorage.removeItem('ant_chat_history');
    const feed = document.getElementById('pm-feed-list');
    if (!feed) return;
    feed.innerHTML = `
      <div class="empty-feed-placeholder" id="pm-empty-placeholder">
        <svg class="placeholder-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        <h4>Project Manager в режиме ожидания</h4>
        <p>Поставьте задачу. PM составит архитектурный план, распределит подзадачи между AI агентами (Разработчик, Дизайнер, QA, DevOps) и полностью создаст готовый проект в рабочей среде.</p>
      </div>
    `;
  }

  togglePMDrawer(open) {
    const d = document.getElementById('pm-console-drawer');
    if (open) d.classList.add('open');
    else d.classList.remove('open');
  }

  toggleLiveWorkspace(open) {
    const d = document.getElementById('live-workspace-drawer');
    if (!d) return;
    if (open) {
      d.classList.add('open');
      if (this.liveWorkspace) this.liveWorkspace.refreshTree();
    } else {
      d.classList.remove('open');
    }
  }

  setupIdleSwarmMonitor() {
    this.lastUserActivity = Date.now();
    this.lastIdlePromptSent = 0;

    ['click', 'keydown', 'input', 'mousemove'].forEach(evt => {
      window.addEventListener(evt, () => {
        this.lastUserActivity = Date.now();
      }, { passive: true });
    });

    setInterval(() => {
      const now = Date.now();
      const idleSeconds = (now - this.lastUserActivity) / 1000;
      // If idle for > 40 seconds, no active tasks running, and not prompted in last 3 minutes
      if (idleSeconds >= 40 && !this.isRunning && (now - this.lastIdlePromptSent) > 180000) {
        this.lastIdlePromptSent = now;
        this.triggerPMIdleInquiry();
      }
    }, 5000);
  }

  async triggerPMIdleInquiry() {
    const feed = document.getElementById('pm-feed-list');
    if (!feed) return;

    const ph = document.getElementById('pm-empty-placeholder');
    if (ph) ph.remove();

    // Xotiradan dinamik ma'lumot olamiz — PM real gapirsin, statik shablon emas
    let greeting = null;
    try {
      const res = await fetch('/api/pm/memory/greeting');
      greeting = await res.json();
    } catch (e) {}

    let bodyHtml;
    if (greeting && greeting.total_orchestrations > 0) {
      const lp = greeting.last_project;
      const plans = greeting.pending_plans || [];
      const stats = `${greeting.total_orchestrations} loyiha (o'rt. ball ${greeting.avg_score || '—'})`;
      const lpBlock = lp
        ? `<p><strong>So'nggi loyiha:</strong> «${this.esc((lp.task || '').slice(0, 120))}» — ${lp.files_count || 0} fayl, ${lp.score !== null ? `ball ${lp.score}` : 'baholanmagan'} <span style="opacity:0.7">(${lp.iso || ''})</span></p>`
        : '';
      const plansBlock = plans.length
        ? `<p><strong>Kelajakdagi rejalar (${greeting.pending_plans_total}):</strong></p><ul style="margin:4px 0 8px 20px;">${plans.map(p => `<li>${this.esc(p.text)}</li>`).join('')}</ul>`
        : '';
      bodyHtml = `
        <p><strong>Уважаемый CEO,</strong> команда закончила текущие задачи. За всё время я обработал ${this.esc(stats)}.</p>
        ${lpBlock}
        ${plansBlock}
        <p>Продолжим один из отложенных планов, или у вас новая идея? Скажите слово — начнём.</p>
      `;
    } else {
      bodyHtml = `
        <p><strong>Уважаемый CEO!</strong> Команда разработчиков (7 AI специалистов) готова к работе.</p>
        <p>Дайте первую задачу — я разложу её на этапы, назначу лучшую модель на каждую роль и организую полный цикл: разработка → тесты → безопасность → деплой.</p>
        <p style="opacity:0.75;font-size:11.5px;">💡 Совет: скажите «запомни, что…» — и я буду держать это в долговременной памяти между сессиями.</p>
      `;
    }

    const pmMsg = document.createElement('div');
    pmMsg.className = 'chat-card chat-card-pm';
    pmMsg.innerHTML = `
      <div class="chat-header">
        <div class="chat-sender">
          <span class="sender-avatar avatar-pm"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg></span>
          <strong>Project Manager & Master Orchestrator</strong>
          <span class="role-badge badge-pm">Проактивный запрос к CEO</span>
        </div>
        <span class="chat-time">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="chat-body formatted-markdown">${bodyHtml}</div>
    `;
    feed.appendChild(pmMsg);
    feed.scrollTop = feed.scrollHeight;

    if (this.canvas && typeof this.canvas.updateStationModel === 'function') {
      this.canvas.updateStationModel('pm', 'DeepSeek V4 Flash', 'Ожидаем задачи от CEO');
    }
  }

  // Foydalanuvchi "запомни / eslab qol" desa — future plan sifatida saqlaymiz
  async detectAndSaveFuturePlan(text) {
    const t = (text || '').trim();
    const patterns = [
      /^(?:запомни|запомните|запомнить)[,\s:]+(.+)$/i,
      /^(?:eslab qol|eslab qoling|eslab qolish)[,\s:]+(.+)$/i,
      /^(?:remember|remember that)[,\s:]+(.+)$/i,
      /^(?:keyinroq|позже|later)[,\s:]+(.+)$/i,
    ];
    for (const rx of patterns) {
      const m = t.match(rx);
      if (m && m[1]) {
        try {
          const res = await fetch('/api/pm/memory/future-plan', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: m[1].trim(), source: 'user'}),
          });
          const data = await res.json();
          return data.success ? m[1].trim() : null;
        } catch(e) { return null; }
      }
    }
    return null;
  }

  async loadRolesOnStartup() {
    try {
      const res = await fetch('/api/roles');
      if (res.ok) {
        const data = await res.json();
        if (data.roles) {
          this.canvas.updateRoles(data.roles);
        }
      }
    } catch (e) {}
  }

  updateLiveHUD(agentName, modelName, actionText, progressPct) {
    const agentEl = document.getElementById('hud-agent-label');
    const modelEl = document.getElementById('hud-model-tag');
    const actionEl = document.getElementById('hud-action-stream');
    const fillEl = document.getElementById('hud-progress-fill');

    if (agentEl && agentName) agentEl.textContent = agentName;
    if (modelEl && modelName) modelEl.textContent = cleanModelLabel(modelName);
    if (actionEl && actionText) actionEl.textContent = actionText;
    if (fillEl && progressPct !== undefined) fillEl.style.width = `${progressPct}%`;
  }

  // Toast notification stack — o'ng yuqori burchakda vaqtinchalik xabarlar
  toast(title, desc = '', type = 'info', duration = 3500) {
    let stack = document.getElementById('ant-toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.id = 'ant-toast-stack';
      document.body.appendChild(stack);
    }
    const icons = { ok: '✓', info: 'ℹ', warn: '⚠', error: '✕' };
    const t = document.createElement('div');
    t.className = `ant-toast type-${type}`;
    t.innerHTML = `
      <span class="toast-ico">${icons[type] || 'ℹ'}</span>
      <div class="toast-body">
        <div class="toast-title">${this.esc(title)}</div>
        ${desc ? `<div class="toast-desc">${this.esc(desc)}</div>` : ''}
      </div>
      <button class="toast-close" title="Закрыть">✕</button>
    `;
    stack.appendChild(t);
    const dismiss = () => {
      if (t._done) return;
      t._done = true;
      t.classList.add('leaving');
      setTimeout(() => t.remove(), 320);
    };
    t.querySelector('.toast-close').addEventListener('click', dismiss);
    if (duration > 0) setTimeout(dismiss, duration);
    return t;
  }

  // Smooth number rollup animation for KPI values — matnda raqam bo'lsa
  // undan oldingi qiymatdan yangi qiymatga ~300ms davomida sanaydi.
  _tweenNumber(el, newText) {
    if (!el) return;
    const oldText = el.textContent || '';
    // Raqam va qo'shimchani ajratamiz (masalan "1.5 GB", "234 tkn", "850 ms", "42")
    const rx = /^([\-\+]?[\d]+(?:[.,]\d+)?)([KMGT]?)\s*(.*)$/;
    const nm = String(newText).match(rx);
    const om = oldText.match(rx);
    if (!nm || !om) {
      el.textContent = newText;
      return;
    }
    const newNum = parseFloat(nm[1].replace(',', '.'));
    const oldNum = parseFloat(om[1].replace(',', '.'));
    if (isNaN(newNum) || isNaN(oldNum) || newNum === oldNum) {
      el.textContent = newText;
      return;
    }
    // Suffix va decimal formati saqlanadi
    const decimals = (nm[1].split('.')[1] || '').length;
    const suffix = (nm[2] || '') + (nm[3] ? ' ' + nm[3] : '');
    const t0 = performance.now();
    const dur = 400;
    if (el._tweenRaf) cancelAnimationFrame(el._tweenRaf);
    const step = (t) => {
      const p = Math.min(1, (t - t0) / dur);
      // ease-out cubic
      const e = 1 - Math.pow(1 - p, 3);
      const v = oldNum + (newNum - oldNum) * e;
      el.textContent = v.toFixed(decimals) + suffix;
      if (p < 1) el._tweenRaf = requestAnimationFrame(step);
      else el.textContent = newText;
    };
    el._tweenRaf = requestAnimationFrame(step);
  }

  async fetchRealStats() {
    try {
      const res = await fetch('/api/hive/real-stats');
      const data = await res.json();

      const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        this._tweenNumber(el, val);
      };

      setEl('val-total-models', data.total_models || '21');
      setEl('sub-online-models', `${data.online_models || 11} в сети`);
      setEl('val-tasks-run', data.total_tasks_run || '0');
      
      const totalK = ((data.total_tokens_consumed || 0) / 1000).toFixed(1);
      setEl('val-total-tokens', `${(data.total_tokens_consumed || 0) > 1000 ? totalK + 'K' : (data.total_tokens_consumed || 0)} tkn`);
      
      const bytes = data.workspace_bytes || 0;
      let sizeStr = '0 KB';
      if (bytes >= 1024 * 1024 * 1024) {
        sizeStr = `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
      } else if (bytes >= 1024 * 1024) {
        sizeStr = `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
      } else {
        sizeStr = `${(bytes / 1024).toFixed(0)} KB`;
      }
      setEl('val-workspace-bytes', sizeStr);
      setEl('sub-workspace-files', `${data.workspace_files_count || 0} файлов`);
      setEl('val-avg-latency', `${data.avg_latency_ms || 850} ms`);

      // Dynamic Health Widget Update
      const healthVal = document.getElementById('val-colony-health');
      if (healthVal) {
        let statusUz = 'Отличное';
        if (data.health_level === 3) statusUz = 'Хорошее';
        else if (data.health_level === 2) statusUz = 'Среднее';
        else if (data.health_level === 1) statusUz = 'Снижено';
        healthVal.innerHTML = `${statusUz} <span class="green-dot" id="dot-colony-health" style="background-color: ${data.health_color || '#10b981'}; box-shadow: 0 0 6px ${data.health_color || '#10b981'}"></span>`;
      }

      const healthDesc = document.getElementById('txt-health-desc');
      const cacheStats = data.prompt_cache || {};
      const savedTokens = cacheStats.tokens_saved || 0;
      if (healthDesc) {
        healthDesc.textContent = `${data.online_models || 11}/${data.total_models || 14} моделей активны • Кэш: ${savedTokens > 1000 ? (savedTokens/1000).toFixed(1) + 'K' : savedTokens} token`;
      }

      const valCache = document.getElementById('val-cache-tokens');
      const subCache = document.getElementById('sub-cache-hit');
      if (valCache) {
        valCache.textContent = savedTokens > 1000 ? (savedTokens / 1000).toFixed(1) + 'K' : savedTokens;
      }
      if (subCache) {
        const hits = cacheStats.cache_hits || cacheStats.hits || 0;
        const hitRate = cacheStats.hit_rate_pct || 0;
        subCache.textContent = `Хит ${hitRate}% (${hits})`;
      }

      const healthLevel = data.health_level || 4;
      const healthColor = data.health_color || '#10b981';
      for (let i = 1; i <= 4; i++) {
        const bar = document.getElementById(`hbar-${i}`);
        if (bar) {
          if (i <= healthLevel) {
            bar.className = 'h-bar active';
            bar.style.backgroundColor = healthColor;
            bar.style.boxShadow = `0 0 5px ${healthColor}`;
          } else {
            bar.className = 'h-bar';
            bar.style.backgroundColor = '';
            bar.style.boxShadow = '';
          }
        }
      }

      // CEO Cache KPI
      const ceoCache = document.getElementById('ceo-kpi-cache');
      if (ceoCache) ceoCache.textContent = `${savedTokens} токенов сэкономлено`;
    } catch (e) {
      console.warn('Real stats error:', e);
    }
  }

  createThinkingCard(feed) {
    let existing = feed.querySelector('.chat-thinking-card.is-thinking');
    if (existing) return existing;

    const thinkingCard = document.createElement('div');
    thinkingCard.className = 'chat-thinking-card is-thinking';
    thinkingCard.innerHTML = `
      <div class="thinking-shimmer-bar"></div>
      <div class="thinking-header">
        <div class="thinking-status-group">
          <svg class="thinking-pulse-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          <span class="thinking-label">Размышление (Thinking)...</span>
          <div class="chat-typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
        <div class="thinking-meta-badge">
          <span class="thinking-token-val">Процесс анализа</span>
          <span class="thinking-arrow">▼</span>
        </div>
      </div>
      <div class="thinking-content">Project Manager анализирует задачу и проектирует архитектуру...</div>
    `;
    thinkingCard.querySelector('.thinking-header').onclick = () => {
      thinkingCard.classList.toggle('collapsed');
    };
    feed.appendChild(thinkingCard);
    return thinkingCard;
  }

  async checkAndReconnectActiveJob() {
    try {
      const res = await fetch('/api/orchestrator/latest');
      if (!res.ok) return;
      const data = await res.json();
      if (!data || !data.job_id || !data.events || data.events.length === 0) return;

      const feed = document.getElementById('pm-feed-list');
      feed.innerHTML = ''; // Clear placeholder
      this.activeThinkingCard = null;

      // Replay all events from server — replay paytida toast'lar CHIQMAYDI,
      // aks holda har reload'da eski "Задача выполнена" toast qayta chiqadi
      this._isReplay = true;
      try {
        data.events.forEach(ev => {
          this.handleOrchestratorEvent(ev, feed);
        });
      } finally {
        this._isReplay = false;
      }

      // If still running on server, reconnect live stream — endi toast'lar
      // faqat yangi (live) event'lar uchun ishlaydi
      if (data.status === 'running') {
        const response = await fetch(`/api/orchestrator/stream/${data.job_id}`);
        if (response.ok) {
          await this.readSSEStream(response, feed);
        }
      }
    } catch (e) {
      console.warn('Reconnect error:', e);
    }
  }

  async readSSEStream(response, feed) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.substring(6));
            this.handleOrchestratorEvent(event, feed);
          } catch (err) {}
        }
      }
    }
    this.saveChatHistory();
  }

  async dispatchPMTask() {
    const input = document.getElementById('pm-task-input');
    const taskText = input.value.trim();
    if (!taskText) return;

    input.value = '';
    const feed = document.getElementById('pm-feed-list');
    const emptyPlaceholder = document.getElementById('pm-empty-placeholder');
    if (emptyPlaceholder) emptyPlaceholder.style.display = 'none';

    // "Запомни..." naqshini aniqlab, orkestratsiya boshlanmasdan xotiraga yozamiz
    const remembered = await this.detectAndSaveFuturePlan(taskText);
    if (remembered) {
      const info = document.createElement('div');
      info.className = 'pm-feed-item';
      info.innerHTML = `<div class="pm-feed-title" style="color:#22c55e;">💾 Запомнено в долговременной памяти</div><div>${this.esc(remembered)}</div><div style="font-size:11px;opacity:0.7;margin-top:4px;">Я буду учитывать это при планировании будущих задач.</div>`;
      feed.appendChild(info);
      feed.scrollTop = feed.scrollHeight;
      this.toast('Запомнено в памяти PM', remembered.slice(0, 80), 'ok');
      return;
    }

    this.isRunning = true;
    this.lastUserActivity = Date.now();
    this.canvas.setActiveStation('pm', 'Составление плана...');
    this.updateLiveHUD('Центральное управление (PM)', 'DeepSeek V4 Flash', `Анализ задачи: ${taskText.slice(0, 35)}...`, 10);

    ['requirements', 'analysis', 'coding', 'testing', 'deploy', 'monitoring'].forEach(id => {
      const el = document.getElementById(`wf-step-${id}`);
      if (el) el.className = 'wf-step';
    });

    try {
      const response = await fetch('/api/orchestrator/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: taskText })
      });

      await this.readSSEStream(response, feed);
    } catch (err) {
      const errItem = document.createElement('div');
      errItem.className = 'pm-feed-item';
      errItem.innerHTML = `<div class="pm-feed-title" style="color:#ef4444">Произошла ошибка</div><div>${this.esc(err.message)}</div>`;
      feed.appendChild(errItem);
      this.saveChatHistory();
    }
  }

  esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  renderMarkdown(text) {
    if (!text) return '';
    let md = String(text).trim();

    // If pure conversational JSON response from model, unwrap the inner text directly
    if (md.startsWith('{') && md.endsWith('}')) {
      try {
        const parsed = JSON.parse(md);
        if (parsed.direct_answer) md = String(parsed.direct_answer);
        else if (parsed.response) md = String(parsed.response);
        else if (parsed.message) md = String(parsed.message);
      } catch (e) {}
    }

    // 1. Strip raw XML tool tags, system markers & emojis
    md = md.replace(/<\/?(?:tool_call|function|parameter|call)[^>]*>/gi, '')
           .replace(/\*\*TASK_COMPLETE\*\*/gi, '')
           .replace(/^---$/gm, '')
           .replace(/[\u{1F300}-\u{1F5FF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F1E0}-\u{1F1FF}]/gu, '')
           .trim();

    // 2. Escape HTML
    md = this.esc(md);

    // 3. Code blocks: ```lang ... ```
    md = md.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const safeLang = lang || 'code';
      const cleanCode = code.trim();
      return `<div class="code-block-wrapper">
        <div class="code-block-header">
          <span class="code-lang-label">${safeLang}</span>
          <button class="btn-copy-code" onclick="navigator.clipboard.writeText(this.closest('.code-block-wrapper').querySelector('code').innerText); this.textContent='Скопировано!'; setTimeout(()=>this.textContent='Копировать', 2000);">Копировать</button>
        </div>
        <pre><code class="language-${safeLang}">${cleanCode}</code></pre>
      </div>`;
    });

    // 4. Inline code: `code`
    md = md.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // 5. Headings
    md = md.replace(/^####\s+(.+)$/gm, '<h4 class="md-h4">$1</h4>')
           .replace(/^###\s+(.+)$/gm, '<h3 class="md-h3">$1</h3>')
           .replace(/^##\s+(.+)$/gm, '<h2 class="md-h2">$1</h2>')
           .replace(/^#\s+(.+)$/gm, '<h1 class="md-h1">$1</h1>');

    // 6. Bold & Italic
    md = md.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    md = md.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 7. Checklists & Lists
    md = md.replace(/^[\*\-]\s+\[x\]\s+(.+)$/gm, '<li class="md-li md-checked"><span class="check-box checked">✓</span> $1</li>');
    md = md.replace(/^[\*\-]\s+\[ \]\s+(.+)$/gm, '<li class="md-li"><span class="check-box">○</span> $1</li>');
    md = md.replace(/^[\*\-]\s+(.+)$/gm, '<li class="md-li">• $1</li>');
    md = md.replace(/(<li class="md-li[\s\S]*?<\/li>)/g, '<ul class="md-ul">$1</ul>');
    md = md.replace(/<\/ul>\s*<ul class="md-ul">/g, '');

    // 8. Paragraphs
    md = md.replace(/\n\n/g, '<p class="md-p"></p>').replace(/\n/g, '<br>');

    return md;
  }

  renderToolCard(event, feed) {
    if (!this.pendingToolCards) this.pendingToolCards = {};

    const isCall = event.action_type === 'tool_call';
    const toolName = event.tool || 'command';
    const step = event.step || 1;
    const cardKey = `${toolName}_${step}`;

    let iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>`;
    if (toolName.includes('file')) {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
    } else if (toolName.includes('shell') || toolName.includes('terminal') || toolName.includes('command')) {
      iconSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`;
    }

    if (isCall) {
      const p = event.params || {};
      let previewTitle = p.filename || p.command || JSON.stringify(p).slice(0, 40);
      let summaryText = '';
      if (p.filename) { summaryText = `Создание/редактирование: ${p.filename}
` + (p.content ? p.content.slice(0, 1000) : ''); }
      else if (p.command) { summaryText = `$ ${p.command}`; }
      else { summaryText = JSON.stringify(p, null, 2); }

      const card = document.createElement('div');
      card.className = 'pm-tool-card is-running';
      card.innerHTML = `
        <div class="tool-card-header" onclick="this.parentElement.classList.toggle('expanded')">
          <div class="tool-header-left">
            <div class="tool-icon-wrap">${iconSvg}</div>
            <span class="tool-name">${this.esc(toolName)}</span>
            <span class="tool-step-badge">#${step}</span>
            <span class="tool-summary-label">${this.esc(previewTitle)}</span>
          </div>
          <div class="tool-header-right">
            <span class="tool-duration"></span>
            <span class="tool-status-pill pill-running">ВЫПОЛНЯЕТСЯ...</span>
            <span class="tool-chevron">▾</span>
          </div>
        </div>
        <div class="tool-card-body">
          <div class="tool-code-preview">
            <pre><code>${this.esc(summaryText)}</code></pre>
          </div>
        </div>
      `;

      feed.appendChild(card);
      feed.scrollTop = feed.scrollHeight;
      this.pendingToolCards[cardKey] = card;
      return card;
    } else {
      // Tool Result Event
      const ok = event.success !== false;
      const duration = event.duration_ms ? `${event.duration_ms}ms` : '';
      const summaryText = this.summarizeToolOutput(event);
      const previewTitle = (summaryText || '').split('\n')[0].slice(0, 55);

      let card = this.pendingToolCards[cardKey];
      if (card && card.parentElement === feed) {
        card.className = `pm-tool-card ${ok ? 'status-ok' : 'status-err'}`;
        const durEl = card.querySelector('.tool-duration');
        if (durEl) durEl.textContent = duration;
        const pillEl = card.querySelector('.tool-status-pill');
        if (pillEl) {
          pillEl.className = `tool-status-pill ${ok ? 'pill-ok' : 'pill-err'}`;
          pillEl.textContent = ok ? 'УСПЕШНО' : 'ОШИБКА';
        }
        const sumEl = card.querySelector('.tool-summary-label');
        if (sumEl) sumEl.textContent = previewTitle;
        const codeEl = card.querySelector('.tool-code-preview code');
        if (codeEl) codeEl.textContent = summaryText;

        delete this.pendingToolCards[cardKey];
        return card;
      } else {
        card = document.createElement('div');
        card.className = `pm-tool-card ${ok ? 'status-ok' : 'status-err'}`;
        card.innerHTML = `
          <div class="tool-card-header" onclick="this.parentElement.classList.toggle('expanded')">
            <div class="tool-header-left">
              <div class="tool-icon-wrap">${iconSvg}</div>
              <span class="tool-name">${this.esc(toolName)}</span>
              <span class="tool-step-badge">#${step}</span>
              <span class="tool-summary-label">${this.esc(previewTitle)}</span>
            </div>
            <div class="tool-header-right">
              ${duration ? `<span class="tool-duration">${duration}</span>` : ''}
              <span class="tool-status-pill ${ok ? 'pill-ok' : 'pill-err'}">${ok ? 'УСПЕШНО' : 'ОШИБКА'}</span>
              <span class="tool-chevron">▾</span>
            </div>
          </div>
          <div class="tool-card-body">
            <div class="tool-code-preview">
              <pre><code>${this.esc(summaryText)}</code></pre>
            </div>
          </div>
        `;
        feed.appendChild(card);
        feed.scrollTop = feed.scrollHeight;
        return card;
      }
    }
  }


  appendFeedItem(feed, options) {
    const item = document.createElement('div');
    item.className = 'pm-feed-item';
    if (options.borderColor) item.style.borderLeftColor = options.borderColor;

    let titleHtml = '';
    if (options.title) {
      const colorStyle = options.titleColor ? `style="color: ${options.titleColor}"` : '';
      titleHtml = `<div class="pm-feed-title" ${colorStyle}>${this.esc(options.title)}</div>`;
    }

    let bodyHtml = '';
    if (options.body) {
      if (options.isMarkdown) {
        bodyHtml = `<div class="formatted-markdown">${this.renderMarkdown(options.body)}</div>`;
      } else if (options.monospace) {
        bodyHtml = `<div class="code-preview-box">${this.esc(options.body)}</div>`;
      } else {
        bodyHtml = `<div>${this.esc(options.body)}</div>`;
      }
    }

    item.innerHTML = titleHtml + bodyHtml;
    feed.appendChild(item);
    feed.scrollTop = feed.scrollHeight;
    return item;
  }

  renderExecutiveSummaryCard(event, feed) {
    const card = document.createElement('div');
    card.className = 'exec-summary-card';

    const createdFiles = event.created_files || [];

    // Conversational javob (oddiy salomlashish yoki savol) — bu haqiqiy loyiha emas.
    // Coder umuman ishlamagan va fayl yaratilmagan → "Задача выполнена 100/100" ko'rsatmaymiz.
    const isConversational = (
      createdFiles.length === 0
      && !event.coder_summary
      && !event.coder_role
      && (event.total_duration_sec || 999) < 30
    );
    if (isConversational) {
      // Kompakt "Ответ дан" ko'rinishi — 100/100 va "Созданные файлы (0)" bo'lmaydi.
      const compact = document.createElement('div');
      compact.className = 'exec-summary-card';
      compact.style.padding = '10px 14px';
      compact.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px; font-size:12px; color:var(--text-muted);">
          <svg style="width:16px; height:16px; color:#22d3ee;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span>Ответ дан · ${event.total_duration_sec || 0}s</span>
        </div>
      `;
      feed.appendChild(compact);
      feed.scrollTop = feed.scrollHeight;
      return;
    }

    let filesHtml = '';
    if (createdFiles.length > 0) {
      filesHtml = createdFiles.map(f => `
        <button class="btn-file-pill" onclick="window.antApp.openFileInWorkspace('${this.esc(f)}')">
          <svg style="width:12px; height:12px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>${this.esc(f)}</span>
        </button>
      `).join('');
    } else {
      filesHtml = '<span style="font-size:11px; color:var(--text-muted)">Созданные файлы yo‘q</span>';
    }

    let scorecardHtml = '';
    if (event.final_score !== undefined) {
      const score = Math.round(event.final_score);
      const bd = event.score_breakdown || {};
      scorecardHtml = `
        <div class="exec-scorecard">
          <div class="scorecard-num">${score}<span>/100</span></div>
          <div class="scorecard-details">
            <div class="scorecard-title">Итоговая оценка качества решения (Continuous evaluation)</div>
            <div class="scorecard-breakdown">
              <span>QA: <strong>${bd.qa !== null && bd.qa !== undefined ? bd.qa : '—'}</strong></span>
              <span>Файлы: <strong>${bd.artifacts ?? '—'}</strong></span>
              <span>Исполнение: <strong>${bd.execution ?? '—'}</strong></span>
              <span>Модель: <strong>${cleanModelLabel(event.coder_model)}</strong></span>
            </div>
          </div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="exec-header">
        <div class="exec-title-group">
          <div class="exec-badge-status">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>ВЫПОЛНЕНО</span>
          </div>
          <div>
            <div class="exec-title-text">Задача успешно выполнена</div>
            <div style="font-size:11px; color:var(--text-muted)">Папка проекта: <code>${event.project_dir || '04_Loyihalar'}</code></div>
          </div>
        </div>
        <div class="exec-meta-duration">${event.total_duration_sec || 12}s</div>
      </div>

      <div class="exec-files-block">
        <div class="exec-files-title">Созданные файлы (${createdFiles.length}):</div>
        <div class="exec-files-pills">${filesHtml}</div>
      </div>

      ${scorecardHtml}

      ${event.coder_summary ? `
        <div class="exec-section-card">
          <div class="exec-section-header">
            <svg style="width:14px; height:14px; color:#6366f1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            <span>Заключение разработчика (${event.coder_role || 'Dasturchi'})</span>
          </div>
          <div class="exec-section-body formatted-markdown">${this.renderMarkdown(event.coder_summary)}</div>
        </div>
      ` : ''}

      ${event.qa_text ? `
        <div class="exec-section-card">
          <div class="exec-section-header">
            <svg style="width:14px; height:14px; color:#06b6d4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
            <span>Заключение тестирования QA (${cleanModelLabel(event.tester_model)})</span>
          </div>
          <div class="exec-section-body formatted-markdown">${this.renderMarkdown(event.qa_text)}</div>
        </div>
      ` : ''}
    `;

    feed.appendChild(card);
    feed.scrollTop = feed.scrollHeight;
  }

  async openFileInWorkspace(filename) {
    await this.openDesktopProjectsModal();
    await this.viewWorkspaceFile(filename);
  }

  summarizeToolOutput(event) {
    const out = event.output;
    if (!out || typeof out !== 'object') return String(out ?? '');
    if (out.error) return `ОШИБКА: ${out.error}`;
    switch (event.tool) {
      case 'write_file':
      case 'edit_file':
        return [`${out.filename} (${out.size_bytes ?? '?'} байт, ${out.lines ?? '?'} строк)`,
                out.syntax_check].filter(Boolean).join(' — ');
      case 'read_file':
        return `${out.filename} прочитан (${out.lines ?? '?'} строк)`;
      case 'list_dir':
        return `${out.total ?? 0} записей: ` +
          (out.entries || []).slice(0, 12).map(e => e.path).join(', ');
      case 'run_shell_command':
        return `$ ${out.command}\nкод возврата=${out.returncode}\n` +
          (out.stdout ? `${out.stdout.slice(0, 700)}\n` : '') +
          (out.stderr ? `stderr: ${out.stderr.slice(0, 400)}` : '');
      case 'execute_python':
        return `код возврата=${out.returncode}\n` +
          (out.stdout ? `${out.stdout.slice(0, 700)}\n` : '') +
          (out.stderr ? `stderr: ${out.stderr.slice(0, 400)}` : '');
      case 'calculate':
        return `${out.expression} = ${out.result}`;
      default:
        return JSON.stringify(out).slice(0, 600);
    }
  }

  handleOrchestratorEvent(event, feed) {
    const type = event.type;

    // 0a. Live Workspace — fayl daraxti va terminal oqimi
    if (type === 'fs_change' && this.liveWorkspace) {
      this.liveWorkspace.handleFsChange(event);
      this.liveWorkspace.setLive(true, 'В эфире');
      return;
    }
    if (type === 'terminal_stream' && this.liveWorkspace) {
      this.liveWorkspace.handleTerminalStream(event);
      this.liveWorkspace.setLive(true, 'В эфире');
      return;
    }
    if (type === 'orchestration_completed' || type === 'orchestration_failed') {
      if (this.liveWorkspace) {
        this.liveWorkspace.setLive(false, type === 'orchestration_completed' ? 'Готово' : 'Остановлено');
        this.liveWorkspace.refreshTree();
      }
      // Toast faqat LIVE event uchun — replay/reload'da qayta chiqmasin.
      // Bundan tashqari conversational (0 fayl + immediate) uchun ham chiqmasin.
      if (!this._isReplay) {
        if (type === 'orchestration_completed') {
          const files = (event.created_files || []).length;
          const isConversational = files === 0 && (event.duration_seconds || 999) < 30;
          if (!isConversational) {
            const score = event.final_score;
            this.toast(
              `Задача выполнена · балл ${score ?? '—'}`,
              `${files} файл${files === 1 ? '' : (files < 5 ? 'а' : 'ов')} создано за ${Math.round(event.duration_seconds || 0)}s`,
              'ok', 5000
            );
          }
        } else {
          this.toast('Оркестрация остановлена', event.error || '', 'error', 6000);
        }
      }
    }
    if (type === 'fs_change' && event.op === 'write' && !this._isReplay) {
      // Faqat oxirgi 700ms da bir toast (spam bo'lmasin)
      const now = Date.now();
      this._lastToastTs = this._lastToastTs || 0;
      if (now - this._lastToastTs > 700) {
        this.toast('Файл записан', event.filename || '', 'info', 2000);
        this._lastToastTs = now;
      }
    }
    if (type === 'user_task' && this.liveWorkspace) {
      this.liveWorkspace.setLive(true, 'Запуск…');
    }

    // 0. User task bubble
    if (type === 'user_task') {
      const placeholder = document.getElementById('pm-empty-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      const userItem = document.createElement('div');
      userItem.className = 'chat-bubble-user';
      userItem.innerHTML = `
        <div class="chat-user-header">
          <div class="chat-user-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <span>Вы (Пользователь)</span>
          </div>
        </div>
        <div class="chat-user-body">${this.esc(event.task)}</div>
      `;
      feed.appendChild(userItem);
      this.activeThinkingCard = this.createThinkingCard(feed);
    }

    // 1. CEO Executive Briefing Updates
    if (type === 'ceo_briefing') {
      const fill = document.getElementById('ceo-meter-fill');
      if (fill) fill.style.width = `${event.progress_pct}%`;
      
      const pTitle = document.getElementById('ceo-phase-title');
      if (pTitle) pTitle.textContent = `${event.progress_pct}% — ${event.phase_title}`;
      
      const sMsg = document.getElementById('ceo-status-msg');
      if (sMsg) sMsg.textContent = event.status_message;
      
      const eta = document.getElementById('ceo-eta-badge');
      if (eta) eta.textContent = `ETA: ${event.eta_seconds}s`;
      
      const agentEl = document.getElementById('ceo-kpi-agent');
      if (agentEl) agentEl.textContent = event.active_agent;
      
      const dirEl = document.getElementById('ceo-kpi-dir');
      if (dirEl) dirEl.textContent = event.project_dir;
      
      const bEl = document.getElementById('ceo-kpi-bottleneck');
      if (bEl) {
        if (event.bottleneck_alert) {
          bEl.textContent = event.bottleneck_alert;
          bEl.className = 'ceo-kpi-val text-amber';
        } else {
          bEl.textContent = "Узких мест нет (Оптимально)";
          bEl.className = 'ceo-kpi-val text-emerald';
        }
      }

      this.updateLiveHUD(event.active_agent, '', event.status_message, event.progress_pct);
    }

    // 2. Workflow Phase transitions
    if (type === 'workflow_phase') {
      const pId = event.phase_id;
      const stId = event.station || 'pm';
      this.canvas.setActiveStation(stId, event.title, cleanModelLabel(event.agent_name));

      const el = document.getElementById(`wf-step-${pId}`);
      if (el) {
        el.classList.add(event.status === 'completed' ? 'completed' : 'active');
      }

      const stepItem = this.appendFeedItem(feed, {
        title: `${event.agent_name || 'Agent'}: ${event.title}`
      });
      stepItem.classList.add('active-phase');
    }

    // 3. Reasoning (Claude / ChatGPT style live streaming)
    if (type === 'reasoning') {
      if (!this.activeThinkingCard || !feed.contains(this.activeThinkingCard)) {
        this.activeThinkingCard = this.createThinkingCard(feed);
      }
      const contentEl = this.activeThinkingCard.querySelector('.thinking-content');
      if (contentEl && event.reasoning_text) contentEl.textContent = event.reasoning_text;
      const badgeEl = this.activeThinkingCard.querySelector('.thinking-token-val');
      if (badgeEl) badgeEl.textContent = `${event.reasoning_tokens || 120} токенов обработано`;
    }

    // 3.1. PM Plan Ready -> Collapse thinking card and show Plan
    if (type === 'pm_plan_ready') {
      if (this.activeThinkingCard) {
        this.activeThinkingCard.classList.remove('is-thinking');
        const lbl = this.activeThinkingCard.querySelector('.thinking-label');
        if (lbl) lbl.textContent = 'Процесс размышления (Reasoning)';
        const badgeEl = this.activeThinkingCard.querySelector('.thinking-token-val');
        if (badgeEl) badgeEl.textContent = `${event.metrics ? event.metrics.reasoning_tokens || 140 : 140} token`;
        const typingDots = this.activeThinkingCard.querySelector('.chat-typing-indicator');
        if (typingDots) typingDots.remove();
        this.activeThinkingCard.classList.add('collapsed');
      }

      const roleLine = event.assigned_role
        ? `\n\n**Назначенный специалист:** ${event.assigned_role} (${cleanModelLabel(event.assigned_model)})`
        : '';
      this.canvas.updateStationModel('pm', cleanModelLabel(event.assigned_model), 'План составлен');
      this.canvas.updateStationModel('coder', cleanModelLabel(event.assigned_model), 'Подготовка');
      this.appendFeedItem(feed, {
        title: 'Архитектурный план Project Manager',
        titleColor: '#8b5cf6', borderColor: '#8b5cf6',
        body: (event.plan_content || '') + roleLine,
        model: cleanModelLabel(event.assigned_model),
        isMarkdown: true
      });
    }

    // 3.2. QA Verified
    if (type === 'qa_verified') {
      const scorePart = event.qa_score !== null && event.qa_score !== undefined
        ? ` — Оценка: ${event.qa_score}/100` : '';
      const roundPart = event.repair_round ? ` (повторная проверка #${event.repair_round})` : '';
      this.canvas.setActiveStation('tester', `QA: ${event.qa_score || 85}/100`);
      this.appendFeedItem(feed, {
        title: `Отчет тестирования QA${scorePart}${roundPart}`,
        titleColor: '#06b6d4', borderColor: '#06b6d4',
        body: event.feedback,
        isMarkdown: true
      });
    }

    // 3.3. Security Audit Report
    if (type === 'security_report') {
      this.canvas.updateStationModel('monitor', cleanModelLabel(event.model), 'Аудит завершен');
      this.appendFeedItem(feed, {
        title: 'Отчет аудита безопасности',
        titleColor: '#f43f5e', borderColor: '#f43f5e',
        body: event.feedback,
        isMarkdown: true
      });
    }

    // 3.4. Specialist agent summary
    if (type === 'agent_message') {
      this.canvas.setActiveStation('coder', 'Решение сдано');
      this.appendFeedItem(feed, {
        title: `${event.agent_name || 'Agent'} заключение (${cleanModelLabel(event.model)})`,
        titleColor: '#6366f1', borderColor: '#6366f1',
        body: event.content,
        isMarkdown: true
      });
    }

    // 3.5. Repair loop
    if (type === 'repair_round_start') {
      this.canvas.setActiveStation('coder', `Исправление #${event.round}`);
      this.appendFeedItem(feed, {
        title: `Цикл исправления #${event.round}`,
        titleColor: '#f97316', borderColor: '#f97316',
        body: event.reason,
        isMarkdown: true
      });
    }

    // 3.6. Model Fallback
    if (type === 'model_fallback') {
      this.appendFeedItem(feed, {
        title: 'Переход на резервную модель',
        titleColor: '#f59e0b', borderColor: '#f59e0b',
        body: event.message
      });
    }

    // 3.7. Agent Errors / Warnings
    if (type === 'agent_error' || type === 'orchestration_failed') {
      this.appendFeedItem(feed, {
        title: `${event.agent_name || 'Оркестратор'}: ошибка`,
        titleColor: '#ef4444', borderColor: '#ef4444',
        body: event.error
      });
    }
    if (type === 'agent_warning') {
      this.appendFeedItem(feed, {
        title: 'Предупреждение', titleColor: '#f59e0b', borderColor: '#f59e0b',
        body: event.message
      });
    }

        // 4. Station Actions & Terminal Commands
    if (type === 'station_action') {
      const st = event.station || 'coder';
      this.canvas.setActiveStation(st, `${event.tool}`);
      this.renderToolCard(event, feed);
    }

    // 5. Role Evaluation Event
    if (type === 'role_evaluation') {
      const b = event.score_breakdown || {};
      const detail = `QA: ${b.qa ?? '—'} • файлы: ${b.artifacts ?? '—'} • исполнение: ${b.execution ?? '—'}`;
      this.appendFeedItem(feed, {
        title: `Модель оценена: ${event.message}`,
        titleColor: '#f59e0b', borderColor: '#f59e0b', body: detail
      });
    }

    // 6. Completion -> Render Executive Summary Card
    if (type === 'orchestration_completed') {
      this.canvas.setActiveStation('pm', 'Задача завершена');
      this.updateLiveHUD('Центральное управление (PM)', 'Все модели активны', 'Проект успешно завершен и сдан', 100);
      this.renderExecutiveSummaryCard(event, feed);
      this.fetchRealStats();
      this.saveChatHistory();
    }
  }

  // --- AI Leaderboard Modal ---
  async openLeaderboardModal() {
    document.getElementById('modal-ai-leaderboard').classList.remove('hidden');
    this.renderLeaderboardData();
  }

  closeLeaderboardModal() {
    document.getElementById('modal-ai-leaderboard').classList.add('hidden');
  }

  formatCategoryName(cat) {
    if (!cat) return 'Общая разработка';
    const map = {
      'planning_pm': 'Project Management',
      'frontend_ui': 'Frontend и UI',
      'backend_api': 'Backend и API',
      'qa_testing': 'QA и тестирование',
      'devops': 'DevOps и деплой',
      'security': 'Аудит безопасности',
      'research': 'Анализ данных',
      'algorithms': 'Алгоритмы и логика',
      'general': 'Общая разработка'
    };
    return map[cat] || cat;
  }

  async renderLeaderboardData() {
    const podiumEl = document.getElementById('leaderboard-podium');
    podiumEl.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:15px; color:#64748b">Загрузка рейтинга...</div>';

    try {
      const res = await fetch('/api/leaderboard');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.leaderboardData = await res.json();

      // 0. "Самый быстрый отклик" bannerini yangilaymiz — avval "Загрузка…"'da qolib qolgan edi
      const fastestNameEl = document.getElementById('lb-fastest-model-name');
      const fastestBadgeEl = document.getElementById('lb-fastest-badge');
      const fm = this.leaderboardData.fastest_model;
      if (fastestNameEl && fastestBadgeEl) {
        if (fm && (fm.model_name || fm.model_id)) {
          fastestNameEl.textContent = fm.model_name || fm.model_id;
          const lat = fm.latency_ms || 0;
          fastestBadgeEl.textContent = `${lat} ms`;
          // Latency rangi
          fastestBadgeEl.className = 'latency-pill ' + (lat < 500 ? 'lat-fast' : lat < 1500 ? 'lat-med' : 'lat-slow');
        } else {
          fastestNameEl.textContent = 'Нет данных';
          fastestBadgeEl.textContent = '— ms';
        }
      }

      // 1. Render Top 3 Podium
      const top3 = this.leaderboardData.top_podium || [];
      podiumEl.innerHTML = '';

      if (top3.length > 0) {
        // Order: #2 Silver, #1 Gold, #3 Bronze for visual podium
        const podiumOrder = [top3[1] || null, top3[0] || null, top3[2] || null];
        podiumOrder.forEach(m => {
          if (!m) return;
          const card = document.createElement('div');
          const medal = m.medal || 'gold';
          card.className = `podium-card ${medal}`;
          
          const medalNum = medal === 'gold' ? '1' : (medal === 'silver' ? '2' : '3');
          const medalLabel = medal === 'gold' ? 'Золото' : (medal === 'silver' ? 'Серебро' : 'Бронза');
          card.innerHTML = `
            <div class="podium-badge-medal">${medalNum}</div>
            <div class="podium-model-name">${m.model_name}</div>
            <div class="podium-provider-tag">${m.provider} • ${medalLabel}</div>
            <div class="podium-score">${m.average_score} ELO</div>
            <div class="podium-category-tag">Лидер: ${this.formatCategoryName(m.best_category)}</div>
          `;
          podiumEl.appendChild(card);
        });
      }

      // 2. Render Table
      this.renderLeaderboardTable();
    } catch (e) {
      podiumEl.innerHTML = `<div style="grid-column: 1/-1; color:#ef4444; padding:10px">Рейтинг не загружен: ${e.message}</div>`;
    }
  }

  renderLeaderboardTable() {
    const tbody = document.getElementById('leaderboard-tbody');
    if (!this.leaderboardData || !this.leaderboardData.rankings) return;

    const cat = this.activeLbCategory;
    let list = [...this.leaderboardData.rankings];

    if (cat !== 'all') {
      list.sort((a, b) => {
        const sa = a.category_scores ? (a.category_scores[cat] || 0) : 0;
        const sb = b.category_scores ? (b.category_scores[cat] || 0) : 0;
        return sb - sa;
      });
    }

    tbody.innerHTML = '';
    list.forEach((m, idx) => {
      const rank = idx + 1;
      const rankClass = rank === 1 ? 'gold' : (rank === 2 ? 'silver' : (rank === 3 ? 'bronze' : ''));
      const score = cat === 'all' ? m.average_score : (m.category_scores ? m.category_scores[cat] || 85 : 85);
      const pct = Math.min(100, Math.max(0, score));

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="lb-rank-num ${rankClass}">#${rank}</span></td>
        <td><strong>${m.model_name}</strong><br><small style="color:#64748b; font-family:var(--font-mono)">${m.model_id}</small></td>
        <td><span style="font-size:11px; background:rgba(139,92,246,0.1); padding:2px 6px; border-radius:4px">${m.provider}</span></td>
        <td>
          <div class="lb-score-bar-wrap">
            <span class="lb-score-val">${score} ELO</span>
            <div class="lb-progress-bar">
              <div class="lb-progress-fill" style="width: ${pct}%"></div>
            </div>
          </div>
        </td>
        <td><span style="font-size:11px; font-weight:600; color:var(--color-purple)">${this.formatCategoryName(m.best_category)}</span></td>
        <td>${m.total_evaluations || 0} оценок</td>
        <td><span style="color:#10b981; font-weight:700">● Онлайн</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --- CEO Modal & Terminal Executor ---
  openCEOBriefingModal() {
    document.getElementById('modal-ceo-briefing').classList.remove('hidden');
  }

  closeCEOBriefingModal() {
    document.getElementById('modal-ceo-briefing').classList.add('hidden');
  }

  async runCEOTerminalCommand() {
    const input = document.getElementById('ceo-terminal-input');
    const cmd = input.value.trim();
    if (!cmd) return;

    const out = document.getElementById('ceo-terminal-output');
    out.textContent = `Выполняется: ${cmd}...`;

    try {
      const res = await fetch('/api/terminal/exec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json();
      out.textContent = `$ ${cmd}\n\n[Код возврата: ${data.returncode}, CWD: ${data.cwd}]\n\nSTDOUT:\n${data.stdout || '(bo‘sh)'}\n\nSTDERR:\n${data.stderr || '(bo‘sh)'}`;
    } catch (e) {
      out.textContent = `Ошибка: ${e.message}`;
    }
  }

  // --- Roles & MD Skills Modal ---
  async openRolesModal() {
    document.getElementById('modal-roles-matrix').classList.remove('hidden');
    const listEl = document.getElementById('roles-cards-list');
    listEl.innerHTML = '<div style="padding:10px; color:#64748b">Загрузка ролей...</div>';

    try {
      const res = await fetch('/api/roles');
      const data = await res.json();
      listEl.innerHTML = '';

      if (!data.roles || data.roles.length === 0) {
        listEl.innerHTML = '<div style="padding:10px; color:#64748b">Роли не найдены.</div>';
        return;
      }

      this.currentRolesData = data.roles;

      data.roles.forEach((r, idx) => {
        const card = document.createElement('div');
        card.className = 'role-card-item' + (idx === 0 ? ' selected' : '');
        card.innerHTML = `
          <div class="role-card-top">
            <span class="role-card-name">${this.esc(r.name)}</span>
            <span class="role-card-score">${r.score || 90} ELO</span>
          </div>
          <div class="role-card-sub">${this.esc(r.description || '')}</div>
          <div style="font-size:10px; color:var(--color-purple); font-family:var(--font-mono); margin-top:2px;">
            Ведущая модель: <strong>${this.esc(r.model_name || r.assigned_model || 'Auto')}</strong>
          </div>
        `;
        card.addEventListener('click', () => {
          listEl.querySelectorAll('.role-card-item').forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          this.viewRoleMD(r);
        });
        listEl.appendChild(card);

        if (idx === 0) this.viewRoleMD(r);
      });
    } catch (e) {
      listEl.innerHTML = `<div style="padding:10px; color:#ef4444">Ошибка: ${e.message}</div>`;
    }
  }

  async viewRoleMD(role) {
    this.activeSelectedRole = role;
    const titleEl = document.getElementById('role-preview-title');
    const contentEl = document.getElementById('role-preview-content');
    const textareaEl = document.getElementById('role-inline-textarea');
    const btnSave = document.getElementById('btn-save-role-inline');
    const btnToggle = document.getElementById('btn-toggle-role-inline-edit');

    if (titleEl) titleEl.textContent = `${role.name} — Инструкции MD`;
    if (contentEl) contentEl.textContent = 'Загрузка инструкции...';
    if (textareaEl) {
      textareaEl.value = 'Загрузка...';
      textareaEl.classList.add('hidden');
    }
    if (contentEl) contentEl.classList.remove('hidden');
    if (btnSave) btnSave.classList.add('hidden');
    if (btnToggle) btnToggle.textContent = 'Редактировать MD';

    try {
      const res = await fetch(`/api/roles/${encodeURIComponent(role.id)}/md`);
      const data = await res.json();
      this.activeSelectedRoleContent = data.md_content || '';
      if (contentEl) contentEl.innerHTML = this.renderMarkdown(data.md_content || 'Инструкция отсутствует');
      if (textareaEl) textareaEl.value = data.md_content || '';
    } catch (e) {
      if (contentEl) contentEl.textContent = `Ошибка загрузки: ${e.message}`;
    }
  }

  toggleRoleInlineEdit() {
    const contentEl = document.getElementById('role-preview-content');
    const textareaEl = document.getElementById('role-inline-textarea');
    const btnSave = document.getElementById('btn-save-role-inline');
    const btnToggle = document.getElementById('btn-toggle-role-inline-edit');

    const isEditing = !textareaEl.classList.contains('hidden');
    if (isEditing) {
      // Switch back to preview
      textareaEl.classList.add('hidden');
      contentEl.classList.remove('hidden');
      contentEl.innerHTML = this.renderMarkdown(textareaEl.value);
      btnSave.classList.add('hidden');
      btnToggle.textContent = 'Редактировать MD';
    } else {
      // Switch to editing
      contentEl.classList.add('hidden');
      textareaEl.classList.remove('hidden');
      btnSave.classList.remove('hidden');
      btnToggle.textContent = 'Просмотр';
      textareaEl.focus();
    }
  }

  async saveRoleInline() {
    if (!this.activeSelectedRole) return;
    const textareaEl = document.getElementById('role-inline-textarea');
    const statusEl = document.getElementById('role-save-status');
    const content = textareaEl.value;
    const mdFile = this.activeSelectedRole.md_file || `${this.activeSelectedRole.id}.md`;

    statusEl.textContent = 'Сохранение...';
    statusEl.style.color = 'var(--text-muted)';

    try {
      const res = await fetch(`/api/skills/${encodeURIComponent(mdFile)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      const data = await res.json();
      if (data.success) {
        statusEl.textContent = 'Сохранено!';
        statusEl.style.color = 'var(--color-emerald)';
        this.activeSelectedRoleContent = content;
      } else {
        statusEl.textContent = 'Ошибка!';
        statusEl.style.color = '#ef4444';
      }
    } catch (e) {
      statusEl.textContent = `Ошибка: ${e.message}`;
      statusEl.style.color = '#ef4444';
    }
    setTimeout(() => { if (statusEl) statusEl.textContent = ''; }, 3000);
  }

  async addCustomRoleModal() {
    const roleName = prompt('Введите название новой роли (например, Security Lead или Blockchain Dev):');
    if (!roleName || !roleName.trim()) return;

    const roleDesc = prompt('Введите краткое описание роли:', 'Специалист по выполнению задач');
    const roleId = roleName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');

    try {
      const res = await fetch('/api/skills/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role_id: roleId,
          name: roleName.trim(),
          category: 'general',
          description: (roleDesc || '').trim(),
          content: `# ${roleName.trim()}\n\n## Описание роли\n${(roleDesc || '').trim()}\n\n## Ключевые навыки (Skills)\n- Экспертное выполнение задач\n`
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Роль «${roleName.trim()}» успешно создана!`);
        this.openRolesModal();
      } else {
        alert('Ошибка при создании роли: ' + JSON.stringify(data));
      }
    } catch (e) {
      alert('Ошибка: ' + e.message);
    }
  }

  closeRolesModal() {
    document.getElementById('modal-roles-matrix').classList.add('hidden');
  }


  // --- Auto Monitoring Models Table ---
  async openModelsModal() {
    document.getElementById('modal-models-hub').classList.remove('hidden');
    this.renderModelsTable();
  }

  async renderModelsTable() {
    const tbody = document.getElementById('colony-models-tbody');
    try {
      const res = await fetch('/api/models');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      tbody.innerHTML = '';

      if (!data.models || data.models.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:12px; color:#64748b">Список моделей пуст</td></tr>';
        return;
      }

      data.models.forEach(m => {
        const isOnline = m.status === 'online';
        const badgeColor = isOnline ? '#10b981' : (m.status === 'rate_limited' ? '#f59e0b' : '#ef4444');
        const statusLabel = isOnline ? 'Online (200 OK)' : (m.status === 'rate_limited' ? '429 Rate limit' : m.status);

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${m.name}</strong><br><small style="color:#64748b">${m.id}</small></td>
          <td><span style="font-size:11px; background:rgba(139,92,246,0.1); padding:2px 6px; border-radius:4px">${m.provider}</span></td>
          <td><span style="color:${badgeColor}; font-weight:700">● ${statusLabel}</span></td>
          <td>${m.latency_ms ? m.latency_ms + ' ms' : '-'}</td>
          <td>${m.uptime_pct}%</td>
          <td>${(m.context_window / 1024).toFixed(0)}K</td>
          <td>
            <button class="btn-hive-action" style="padding:3px 8px; font-size:11px" onclick="window.antApp.pingSingleModel('${m.id}')">Ping</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7" style="color:#ef4444; padding:10px">Ошибка: ${e.message}</td></tr>`;
    }
  }

  closeModelsModal() {
    document.getElementById('modal-models-hub').classList.add('hidden');
  }

  async pingAllModels() {
    await fetch('/api/models/ping-all', { method: 'POST' });
    this.fetchRealStats();
    this.renderModelsTable();
  }

  async pingSingleModel(modelId) {
    await fetch('/api/models/ping-single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId })
    });
    this.renderModelsTable();
  }

  // --- Workspace / Ishchi Muhit Modal ---
  async openDesktopProjectsModal() {
    document.getElementById('modal-workspace').classList.remove('hidden');
    const listEl = document.getElementById('modal-files-list');
    listEl.innerHTML = '<div style="padding:10px; color:#64748b">Загрузка файлов рабочей среды...</div>';

    try {
      const res = await fetch('/api/workspace/files');
      const data = await res.json();
      listEl.innerHTML = '';

      if (!data.files || data.files.length === 0) {
        listEl.innerHTML = '<div style="padding:10px; color:#64748b">Файлы пока отсутствуют.</div>';
        return;
      }

      data.files.forEach((f, idx) => {
        const item = document.createElement('button');
        item.className = `nav-item ${idx === 0 ? 'active' : ''}`;
        item.style.width = '100%';
        item.style.justifyContent = 'space-between';
        item.innerHTML = `
          <span>${f.name}</span>
          <small style="color:#64748b">${(f.size / 1024).toFixed(1)} KB</small>
        `;
        item.addEventListener('click', () => {
          listEl.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
          item.classList.add('active');
          this.viewWorkspaceFile(f.name);
        });
        listEl.appendChild(item);

        if (idx === 0) this.viewWorkspaceFile(f.name);
      });
    } catch (e) {
      listEl.innerHTML = `<div style="color:#ef4444; padding:10px">Ошибка: ${e.message}</div>`;
    }
  }

  async viewWorkspaceFile(filename) {
    const codeEl = document.getElementById('modal-file-code');
    codeEl.textContent = 'Загрузка...';
    try {
      const res = await fetch(`/api/workspace/files/${encodeURIComponent(filename)}`);
      const data = await res.json();
      codeEl.textContent = data.content || '// Fayl bo‘sh';
    } catch (e) {
      codeEl.textContent = `Ошибка: ${e.message}`;
    }
  }

  closeDesktopProjectsModal() {
    document.getElementById('modal-workspace').classList.add('hidden');
  }

  // --- Open-Source Setup Wizard Modal ---
  async checkFirstRunSetup() {
    try {
      const res = await fetch('/api/setup/status');
      const data = await res.json();
      if (data && data.configured === false) {
        this.openSetupModal();
      }
    } catch (e) {
      console.warn('Setup status check warning:', e);
    }
  }

  openSetupModal() {
    const savedRecMode = localStorage.getItem('ant_recreation_mode') || 'auto';
    const recRadio = document.querySelector(`input[name="recreation_mode_radio"][value="${savedRecMode}"]`);
    if (recRadio) recRadio.checked = true;
    document.getElementById('modal-setup-wizard').classList.remove('hidden');
    const chatterToggle = document.getElementById('setup-ai-chatter-toggle');
    if (chatterToggle) {
      chatterToggle.checked = localStorage.getItem('ant_ai_chatter_enabled') !== 'false';
    }
    // Workspace va generation sozlamalarni yuklaymiz
    this.refreshWorkspaceStatus();
    this.refreshGenSettings();
  }

  closeSetupModal() {
    document.getElementById('modal-setup-wizard').classList.add('hidden');
    const br = document.getElementById('ws-browser');
    if (br) br.classList.add('hidden');
  }

  async refreshGenSettings() {
    try {
      const res = await fetch('/api/setup/generation-settings');
      const g = await res.json();
      const tEl = document.getElementById('gen-temperature');
      const tVal = document.getElementById('gen-temp-val');
      const mEl = document.getElementById('gen-max-tokens');
      const vEl = document.getElementById('gen-vision');
      const fEl = document.getElementById('gen-free-only');
      if (tEl) tEl.value = g.default_temperature;
      if (tVal) tVal.textContent = Number(g.default_temperature).toFixed(2);
      if (mEl) mEl.value = g.default_max_tokens;
      if (vEl) vEl.checked = !!g.enable_vision;
      if (fEl) fEl.checked = !!g.free_models_only;
    } catch (e) {}
  }

  async saveGenSettings() {
    const t = parseFloat(document.getElementById('gen-temperature').value);
    const m = parseInt(document.getElementById('gen-max-tokens').value, 10);
    const v = document.getElementById('gen-vision').checked;
    const f = document.getElementById('gen-free-only').checked;
    try {
      const res = await fetch('/api/setup/generation-settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({default_temperature: t, default_max_tokens: m, enable_vision: v, free_models_only: f}),
      });
      const data = await res.json();
      if (data.success) {
        this.toast('Параметры сохранены', `temp=${t}, max_tokens=${m}, vision=${v ? 'вкл' : 'выкл'}, free=${f ? 'да' : 'нет'}`, 'ok');
      } else {
        this.toast('Ошибка', data.error || '—', 'error');
      }
    } catch (e) {
      this.toast('Сеть', e.message, 'error');
    }
  }

  async fetchFreeModels() {
    const listEl = document.getElementById('gen-free-list');
    if (!listEl) return;
    listEl.classList.remove('hidden');
    listEl.innerHTML = '<div style="text-align:center; color:#22d3ee;">Загрузка бесплатных моделей…</div>';
    try {
      const res = await fetch('/api/setup/fetch-free-models', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({provider: 'openrouter'}),
      });
      const data = await res.json();
      if (data.success && data.models) {
        if (data.models.length === 0) {
          listEl.innerHTML = '<div style="color:var(--text-muted); text-align:center;">Бесплатных моделей не найдено</div>';
          return;
        }
        listEl.innerHTML = `
          <div style="margin-bottom:8px; font-weight:700; color:#22d3ee;">Найдено бесплатных моделей: ${data.count}</div>
          ${data.models.slice(0, 40).map(m => `
            <div class="free-model-row">
              <span>${this.esc(m.name || m.id)}</span>
              <span class="model-ctx">${m.context_window ? (m.context_window / 1000).toFixed(0) + 'K' : '—'}</span>
            </div>
          `).join('')}
          ${data.models.length > 40 ? `<div style="color:var(--text-muted); text-align:center; margin-top:6px;">… и ещё ${data.models.length - 40}</div>` : ''}
        `;
        this.toast('Бесплатные модели', `Загружено ${data.count} моделей от OpenRouter`, 'ok');
      } else {
        listEl.innerHTML = `<div style="color:#ef4444;">Ошибка: ${this.esc(data.error || '?')}</div>`;
      }
    } catch (e) {
      listEl.innerHTML = `<div style="color:#ef4444;">Сеть: ${this.esc(e.message)}</div>`;
    }
  }

  async refreshWorkspaceStatus() {
    try {
      const res = await fetch('/api/setup/status');
      const data = await res.json();
      const dir = data.projects_dir || '';
      const input = document.getElementById('setup-workspace-path');
      const curPath = document.getElementById('ws-current-path');
      const janInfo = document.getElementById('ws-janitor-info');
      if (input && !input.value) input.value = dir;
      if (curPath) curPath.textContent = dir + (data.projects_dir_exists ? '' : ' (не существует)');
      if (janInfo && data.janitor) {
        const j = data.janitor;
        janInfo.textContent = j.enabled
          ? `${j.watched_folders} набл. · удалено ${j.removed_total}`
          : 'выключен';
      }
    } catch (e) {
      const janInfo = document.getElementById('ws-janitor-info');
      if (janInfo) janInfo.textContent = 'ошибка';
    }
  }

  async applyWorkspaceDir() {
    const input = document.getElementById('setup-workspace-path');
    const path = (input.value || '').trim();
    if (!path) return;
    const curPath = document.getElementById('ws-current-path');
    if (curPath) curPath.textContent = 'применяется…';
    try {
      const res = await fetch('/api/setup/workspace-dir', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path, create_if_missing: true}),
      });
      const data = await res.json();
      if (data.success) {
        if (curPath) curPath.textContent = data.projects_dir + ' ✓';
        // Live Workspace daraxtini ham yangilaymiz
        if (this.liveWorkspace) this.liveWorkspace.refreshTree();
      } else {
        if (curPath) curPath.textContent = 'ошибка: ' + (data.detail || data.error || '?');
      }
    } catch (e) {
      if (curPath) curPath.textContent = 'сеть: ' + e.message;
    }
  }

  async toggleWorkspaceBrowser() {
    const br = document.getElementById('ws-browser');
    if (!br) return;
    if (br.classList.contains('hidden')) {
      const input = document.getElementById('setup-workspace-path');
      const start = (input.value || '~/Desktop').trim() || '~';
      await this._loadBrowserDir(start);
      br.classList.remove('hidden');
    } else {
      br.classList.add('hidden');
    }
  }

  async _loadBrowserDir(path) {
    const list = document.getElementById('ws-browser-list');
    const cwdEl = document.getElementById('ws-browser-cwd');
    if (!list) return;
    list.innerHTML = '<div class="lw-placeholder">загрузка…</div>';
    try {
      const res = await fetch('/api/setup/browse-dir', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path}),
      });
      const data = await res.json();
      if (data.entries) {
        cwdEl.textContent = data.path;
        this._browserCwd = data.path;
        this._browserParent = data.parent;
        list.innerHTML = '';
        // "Выбрать эту папку" row
        const selectRow = document.createElement('div');
        selectRow.className = 'ws-dir-item ws-dir-select';
        selectRow.textContent = `Выбрать текущую: ${data.path}`;
        selectRow.addEventListener('click', () => {
          document.getElementById('setup-workspace-path').value = data.path;
          document.getElementById('ws-browser').classList.add('hidden');
        });
        list.appendChild(selectRow);
        for (const e of data.entries) {
          const row = document.createElement('div');
          row.className = 'ws-dir-item';
          row.textContent = e.name;
          row.addEventListener('click', () => this._loadBrowserDir(e.path));
          list.appendChild(row);
        }
        if (!data.entries.length) {
          const em = document.createElement('div');
          em.className = 'lw-placeholder';
          em.textContent = 'пустая папка';
          list.appendChild(em);
        }
      } else {
        list.innerHTML = `<div class="lw-placeholder">ошибка: ${(data.detail || data.error || '?')}</div>`;
      }
    } catch (e) {
      list.innerHTML = `<div class="lw-placeholder">сеть: ${e.message}</div>`;
    }
  }

  async browserGoUp() {
    if (this._browserParent) await this._loadBrowserDir(this._browserParent);
  }

  async testProviderKey(scope) {
    // scope: 'single', 'github', 'openrouter', 'gemini', 'openai'
    let provider, key;
    if (scope === 'single') {
      provider = document.getElementById('setup-single-provider').value;
      key = document.getElementById('setup-single-key').value.trim();
    } else {
      provider = scope;
      const el = document.getElementById(`setup-multi-${scope}`);
      key = el ? el.value.trim() : '';
    }
    const resultId = scope === 'single' ? 'key-test-single' : `key-test-${scope}`;
    const resultEl = document.getElementById(resultId);
    if (!key) {
      if (resultEl) { resultEl.className = 'key-test-result err'; resultEl.textContent = 'введите ключ'; }
      return;
    }
    if (resultEl) { resultEl.className = 'key-test-result'; resultEl.textContent = 'проверка…'; }
    try {
      const res = await fetch('/api/setup/test-key', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({provider, api_key: key}),
      });
      const data = await res.json();
      if (data.success) {
        if (resultEl) { resultEl.className = 'key-test-result ok'; resultEl.textContent = '✓ ' + (data.message || 'OK'); } window.showToast('API ключ активен', `${scope.toUpperCase()}: соединение установлено`, 'success');
      } else {
        if (resultEl) { resultEl.className = 'key-test-result err'; resultEl.textContent = '✗ ' + (data.error || `HTTP ${data.status}`); } window.showToast('Ошибка API ключа', data.error || 'Неверный ключ', 'error');
      }
    } catch (e) {
      if (resultEl) { resultEl.className = 'key-test-result err'; resultEl.textContent = 'сеть: ' + e.message; }
    }
  }

  async saveSetupConfig() {
    const statusMsg = document.getElementById('setup-status-msg');
    statusMsg.textContent = 'Сохранение и проверка настроек...';
    statusMsg.style.color = 'var(--text-secondary)';

    const activeTab = document.querySelector('#setup-mode-tabs .lb-filter-btn.active');
    const mode = activeTab ? activeTab.getAttribute('data-mode') : 'single';

    // Save Recreation & Sport Zones Mode
    const recRadio = document.querySelector('input[name="recreation_mode_radio"]:checked');
    if (recRadio) {
      localStorage.setItem('ant_recreation_mode', recRadio.value);
      if (this.canvas && typeof this.canvas.setRecreationVisibility === 'function') {
        this.canvas.setRecreationVisibility(recRadio.value, this.isRunning);
      }
    }

    // Save AI Chatter Switch
    const chatterToggle = document.getElementById('setup-ai-chatter-toggle');
    if (chatterToggle) {
      localStorage.setItem('ant_ai_chatter_enabled', chatterToggle.checked ? 'true' : 'false');
    }

    const payload = { mode };

    if (mode === 'single') {
      const prov = document.getElementById('setup-single-provider').value;
      const key = document.getElementById('setup-single-key').value.trim();
      payload.provider = prov;
      if (prov === 'github') payload.github_key = key;
      else if (prov === 'openrouter') payload.openrouter_key = key;
      else if (prov === 'gemini') payload.gemini_key = key;
      else if (prov === 'openai') payload.openai_key = key;
      else if (prov === 'groq') payload.groq_key = key;
    } else if (mode === 'multi') {
      payload.github_key = document.getElementById('setup-multi-github').value.trim();
      payload.openrouter_key = document.getElementById('setup-multi-openrouter').value.trim();
      payload.gemini_key = document.getElementById('setup-multi-gemini').value.trim();
      payload.openai_key = document.getElementById('setup-multi-openai').value.trim();
    } else if (mode === 'custom') {
      payload.custom_base_url = document.getElementById('setup-custom-url').value.trim();
      payload.custom_key = document.getElementById('setup-custom-key').value.trim();
    } else if (mode === 'telegram') {
      document.getElementById('btn-save-tg-bot')?.click();
      statusMsg.textContent = 'Telegram бот настроен!';
      statusMsg.style.color = '#10b981';
      return;
    }

    try {
      const res = await fetch('/api/setup/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        statusMsg.textContent = '[OK] Настройки успешно сохранены!';
        statusMsg.style.color = '#10b981';
        window.showToast('Настройки сохранены', 'Конфигурация API и режим зон успешно применены', 'success');
        this.fetchRealStats();
        setTimeout(() => this.closeSetupModal(), 1200);
      } else {
        window.showToast('Ошибка сохранения', data.message || 'Проверьте API ключ', 'error');
        statusMsg.textContent = `Ошибка: ${data.message || 'Saqlab bo‘lmadi'}`;
        statusMsg.style.color = '#ef4444';
      }
    } catch (e) {
      statusMsg.textContent = `Ошибка: ${e.message}`;
      statusMsg.style.color = '#ef4444';
    }
  }
}


// ============================================================
// SKILL & ROLE EDITOR
// ============================================================
let _activeSkillFile = null;

async function openSkillEditor(targetFname = null) {
  document.getElementById('modal-skill-editor').classList.remove('hidden');
  const listEl = document.getElementById('skill-file-list');
  listEl.innerHTML = '<div style="padding:10px; color:#64748b; font-size:12px;">Загрузка...</div>';
  try {
    const res = await fetch('/api/skills');
    const data = await res.json();
    listEl.innerHTML = '';
    if (!data.files || data.files.length === 0) {
      listEl.innerHTML = '<div style="padding:10px; color:#64748b; font-size:12px;">Файлы навыков не найдены.</div>';
      return;
    }
    const target = targetFname || data.files[0];
    data.files.forEach((fname) => {
      const btn = document.createElement('button');
      btn.className = 'editor-file-btn' + (fname === target ? ' active' : '');
      btn.textContent = fname;
      btn.addEventListener('click', () => {
        listEl.querySelectorAll('.editor-file-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadSkillFile(fname);
      });
      listEl.appendChild(btn);
    });
    if (target) loadSkillFile(target);
  } catch (e) {
    listEl.innerHTML = `<div style="padding:10px; color:#ef4444; font-size:12px;">Ошибка: ${e.message}</div>`;
  }
}

async function loadSkillFile(fname) {
  _activeSkillFile = fname;
  const textarea = document.getElementById('skill-editor-textarea');
  const label = document.getElementById('skill-current-file');
  const status = document.getElementById('skill-save-status');
  label.textContent = fname;
  status.textContent = '';
  textarea.value = 'Загрузка...';
  try {
    const res = await fetch(`/api/skills/${encodeURIComponent(fname)}`);
    const data = await res.json();
    textarea.value = data.content || '';
  } catch (e) {
    textarea.value = `Ошибка: ${e.message}`;
  }
}

async function saveSkillFile() {
  if (!_activeSkillFile) return;
  const content = document.getElementById('skill-editor-textarea').value;
  const status = document.getElementById('skill-save-status');
  status.textContent = 'Сохранение...';
  status.style.color = 'var(--text-muted)';
  try {
    const res = await fetch(`/api/skills/${encodeURIComponent(_activeSkillFile)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    const data = await res.json();
    if (data.success) {
      status.textContent = 'Сохранено!';
      status.style.color = 'var(--color-emerald)';
    } else {
      status.textContent = 'Ошибка!';
      status.style.color = '#ef4444';
    }
  } catch (e) {
    status.textContent = `Ошибка: ${e.message}`;
    status.style.color = '#ef4444';
  }
  setTimeout(() => { const s = document.getElementById('skill-save-status'); if (s) s.textContent = ''; }, 3000);
}

async function createNewSkillFile() {
  const roleName = prompt('Введите название навыка / роли (например, Performance Tester):');
  if (!roleName || !roleName.trim()) return;

  const roleId = roleName.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');
  const initialContent = `# ${roleName.trim()}\n\n## Описание роли\nСпециалист по выполнению профильных задач.\n\n## Ключевые навыки (Skills)\n- Анализ и реализация\n- Оптимизация\n`;

  try {
    const res = await fetch('/api/skills/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role_id: roleId,
        name: roleName.trim(),
        description: 'Пользовательский навык',
        content: initialContent
      })
    });
    const data = await res.json();
    if (data.success) {
      await openSkillEditor(data.filename);
    } else {
      alert('Ошибка создания файла: ' + JSON.stringify(data));
    }
  } catch (e) {
    alert('Ошибка: ' + e.message);
  }
}

// ============================================================
// MARKDOWN EDITOR
// ============================================================
let _activeMdFile = null;

async function openMdEditor(targetFname = null) {
  document.getElementById('modal-md-editor').classList.remove('hidden');
  const listEl = document.getElementById('md-file-list');
  listEl.innerHTML = '<div style="padding:10px; color:#64748b; font-size:12px;">Загрузка...</div>';
  try {
    const res = await fetch('/api/md');
    const data = await res.json();
    listEl.innerHTML = '';
    if (!data.files || data.files.length === 0) {
      listEl.innerHTML = '<div style="padding:10px; color:#64748b; font-size:12px;">MD файлы не найдены.</div>';
      return;
    }
    const target = targetFname || data.files[0];
    data.files.forEach((fname) => {
      const btn = document.createElement('button');
      btn.className = 'editor-file-btn' + (fname === target ? ' active' : '');
      btn.textContent = fname;
      btn.title = fname;
      btn.addEventListener('click', () => {
        listEl.querySelectorAll('.editor-file-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadMdFile(fname);
      });
      listEl.appendChild(btn);
    });
    if (target) loadMdFile(target);
  } catch (e) {
    listEl.innerHTML = `<div style="padding:10px; color:#ef4444; font-size:12px;">Ошибка: ${e.message}</div>`;
  }
}

async function loadMdFile(fname) {
  _activeMdFile = fname;
  const textarea = document.getElementById('md-editor-textarea');
  const label = document.getElementById('md-current-file');
  const status = document.getElementById('md-save-status');
  const shortName = fname.split('/').pop();
  label.textContent = shortName;
  status.textContent = '';
  textarea.value = 'Загрузка...';
  try {
    const res = await fetch(`/api/md/${encodeURIComponent(fname)}`);
    const data = await res.json();
    textarea.value = data.content || '';
  } catch (e) {
    textarea.value = `Ошибка: ${e.message}`;
  }
}

async function saveMdFile() {
  if (!_activeMdFile) return;
  const content = document.getElementById('md-editor-textarea').value;
  const status = document.getElementById('md-save-status');
  status.textContent = 'Сохранение...';
  status.style.color = 'var(--text-muted)';
  try {
    const res = await fetch(`/api/md/${encodeURIComponent(_activeMdFile)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    const data = await res.json();
    if (data.success) {
      status.textContent = 'Сохранено!';
      status.style.color = 'var(--color-emerald)';
    } else {
      status.textContent = 'Ошибка!';
      status.style.color = '#ef4444';
    }
  } catch (e) {
    status.textContent = `Ошибка: ${e.message}`;
    status.style.color = '#ef4444';
  }
  setTimeout(() => { const s = document.getElementById('md-save-status'); if (s) s.textContent = ''; }, 3000);
}

async function createNewMdFile() {
  const fileName = prompt('Введите имя нового файла Markdown (например, API_DOCS.md или ARCHITECTURE.md):');
  if (!fileName || !fileName.trim()) return;

  const cleanName = fileName.trim();
  const initialContent = `# ${cleanName.replace(/\.md$/i, '')}\n\nНовый документ Markdown.\n`;

  try {
    const res = await fetch('/api/md/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: cleanName,
        content: initialContent
      })
    });
    const data = await res.json();
    if (data.success) {
      await openMdEditor(data.filename);
    } else {
      alert('Ошибка создания файла: ' + JSON.stringify(data));
    }
  } catch (e) {
    alert('Ошибка: ' + e.message);
  }
}

// ============================================================
// DYNAMIC PROVIDER MODELS FETCH & IMPORT
// ============================================================
let _discoveredCustomModels = [];

async function fetchCustomProviderModels() {
  const urlInput = document.getElementById('setup-custom-url');
  const keyInput = document.getElementById('setup-custom-key');
  const btn = document.getElementById('btn-fetch-custom-models');
  const box = document.getElementById('custom-models-fetch-box');
  const countLabel = document.getElementById('custom-models-count-label');
  const chipsList = document.getElementById('custom-models-list-chips');

  const baseUrl = (urlInput ? urlInput.value : '').trim();
  const apiKey = (keyInput ? keyInput.value : '').trim();

  if (!baseUrl) {
    alert('Пожалуйста, укажите Base URL провайдера (например, http://localhost:11434/v1 или https://openrouter.ai/api/v1)');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Загрузка...';

  try {
    const res = await fetch('/api/models/fetch-from-provider', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
    });
    const data = await res.json();

    if (data.success && data.models && data.models.length > 0) {
      _discoveredCustomModels = data.models;
      box.classList.remove('hidden');
      countLabel.textContent = `Обнаружено моделей: ${data.count} (${data.latency_ms}ms)`;
      chipsList.innerHTML = '';

      data.models.slice(0, 50).forEach(m => {
        const chip = document.createElement('div');
        chip.className = 'custom-model-chip';
        chip.innerHTML = `<span>●</span> <strong>${m.id}</strong>`;
        chipsList.appendChild(chip);
      });
    } else {
      alert(`Не удалось загрузить модели с ${baseUrl}: ${data.error || 'Список моделей пуст'}`);
    }
  } catch (e) {
    alert('Ошибка запроса: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Загрузить список моделей';
  }
}

async function importAllCustomModels() {
  if (!_discoveredCustomModels || _discoveredCustomModels.length === 0) {
    alert('Сначала загрузите список моделей!');
    return;
  }
  const urlInput = document.getElementById('setup-custom-url');
  const keyInput = document.getElementById('setup-custom-key');
  const baseUrl = (urlInput ? urlInput.value : '').trim();
  const apiKey = (keyInput ? keyInput.value : '').trim();

  try {
    const res = await fetch('/api/models/import-custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        base_url: baseUrl,
        api_key: apiKey,
        models: _discoveredCustomModels
      })
    });
    const data = await res.json();
    if (data.success) {
      alert(`Успешно импортировано ${data.count} моделей в систему Ant Colony AI!`);
      if (window.antApp) {
        window.antApp.fetchRealStats();
      }
    }
  } catch (e) {
    alert('Ошибка импорта: ' + e.message);
  }
}


async function deleteSkillFile() {
  if (!_activeSkillFile) {
    window.showToast('Файл не выбран', 'Выберите файл для удаления', 'warning');
    return;
  }
  if (!confirm(`Вы действительно хотите удалить файл ${_activeSkillFile}?`)) return;

  try {
    const res = await fetch(`/api/skills/${_activeSkillFile}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      window.showToast('Файл удален', `Файл ${_activeSkillFile} успешно удален`, 'info');
      _activeSkillFile = null;
      document.getElementById('skill-current-file').textContent = 'Файл не выбран';
      document.getElementById('skill-editor-code').value = '';
      openSkillEditor(); // Refresh list
    } else {
      window.showToast('Ошибка удаления', data.detail || data.error, 'error');
    }
  } catch (e) {
    window.showToast('Ошибка сети', e.message, 'error');
  }
}

async function deleteMdFile() {
  if (!_activeMdFile) {
    window.showToast('Документ не выбран', 'Выберите документ для удаления', 'warning');
    return;
  }
  if (!confirm(`Вы действительно хотите удалить документ ${_activeMdFile}?`)) return;

  try {
    const res = await fetch(`/api/md/${_activeMdFile}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      window.showToast('Документ удален', `Файл ${_activeMdFile} успешно удален`, 'info');
      _activeMdFile = null;
      document.getElementById('md-current-file').textContent = 'Файл не выбран';
      document.getElementById('md-editor-code').value = '';
      openMdEditor(); // Refresh list
    } else {
      window.showToast('Ошибка удаления', data.detail || data.error, 'error');
    }
  } catch (e) {
    window.showToast('Ошибка сети', e.message, 'error');
  }
}


// Global DOM Events Wiring
window.addEventListener('DOMContentLoaded', () => {
  window.antApp = new AntColonyApp();

  // Tools Dropdown Toggle (Direct & Reliable)
  const btnToolsDropdown = document.getElementById('btn-top-tools-dropdown');
  const toolsMenu = document.getElementById('tools-dropdown-menu');
  if (btnToolsDropdown && toolsMenu) {
    btnToolsDropdown.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      toolsMenu.classList.toggle('hidden');
    };

    document.addEventListener('click', (e) => {
      if (!btnToolsDropdown.contains(e.target) && !toolsMenu.contains(e.target)) {
        toolsMenu.classList.add('hidden');
      }
    });

    toolsMenu.querySelectorAll('.menu-dropdown-item').forEach(item => {
      item.onclick = () => {
        toolsMenu.classList.add('hidden');
      };
    });
  }

  // Setup Wizard Tabs
  const setupTabs = document.getElementById('setup-mode-tabs');
  if (setupTabs) {
    setupTabs.addEventListener('click', (e) => {
      const btn = e.target.closest('.lb-filter-btn');
      if (!btn) return;
      setupTabs.querySelectorAll('.lb-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.getAttribute('data-mode');
      document.getElementById('panel-setup-single').classList.toggle('hidden', mode !== 'single');
      document.getElementById('panel-setup-multi').classList.toggle('hidden', mode !== 'multi');
      document.getElementById('panel-setup-custom').classList.toggle('hidden', mode !== 'custom');
      const recPanel = document.getElementById('panel-setup-recreation');
      if (recPanel) recPanel.classList.toggle('hidden', mode !== 'recreation');
      const tgPanel = document.getElementById('panel-setup-telegram');
      if (tgPanel) {
        tgPanel.classList.toggle('hidden', mode !== 'telegram');
        if (mode === 'telegram') window.antApp.loadTelegramBotStatus();
      }
    });
  }

  const btnSetupClose = document.getElementById('btn-close-setup-modal');
  if (btnSetupClose) btnSetupClose.addEventListener('click', () => window.antApp.closeSetupModal());
  const btnSetupSave = document.getElementById('btn-setup-save');
  if (btnSetupSave) btnSetupSave.addEventListener('click', () => window.antApp.saveSetupConfig());

  // Workspace directory controls
  const btnWsApply = document.getElementById('btn-ws-apply');
  if (btnWsApply) btnWsApply.addEventListener('click', () => window.antApp.applyWorkspaceDir());
  const btnWsBrowse = document.getElementById('btn-ws-browse');
  if (btnWsBrowse) btnWsBrowse.addEventListener('click', () => window.antApp.toggleWorkspaceBrowser());
  const btnWsUp = document.getElementById('btn-ws-up');
  if (btnWsUp) btnWsUp.addEventListener('click', () => window.antApp.browserGoUp());
  const btnWsBrClose = document.getElementById('btn-ws-browser-close');
  if (btnWsBrClose) btnWsBrClose.addEventListener('click', () => {
    document.getElementById('ws-browser').classList.add('hidden');
  });
  // API key test buttons (event delegation for all .btn-key-test)
  document.querySelectorAll('.btn-key-test').forEach(btn => {
    btn.addEventListener('click', () => {
      const scope = btn.getAttribute('data-test-provider');
      window.antApp.testProviderKey(scope);
    });
  });

  // Generation settings controls
  const genTemp = document.getElementById('gen-temperature');
  const genTempVal = document.getElementById('gen-temp-val');
  if (genTemp && genTempVal) {
    genTemp.addEventListener('input', () => {
      genTempVal.textContent = Number(genTemp.value).toFixed(2);
    });
  }
  const btnSaveGen = document.getElementById('btn-save-gen-settings');
  if (btnSaveGen) btnSaveGen.addEventListener('click', () => window.antApp.saveGenSettings());
  const btnFreeModels = document.getElementById('btn-fetch-free-openrouter');
  if (btnFreeModels) btnFreeModels.addEventListener('click', () => window.antApp.fetchFreeModels());

  // Custom provider fetch & import
  const btnFetchModels = document.getElementById('btn-fetch-custom-models');
  if (btnFetchModels) btnFetchModels.addEventListener('click', () => fetchCustomProviderModels());
  const btnImportModels = document.getElementById('btn-import-all-custom-models');
  if (btnImportModels) btnImportModels.addEventListener('click', () => importAllCustomModels());

  // Roles modal actions
  const btnToggleRoleEdit = document.getElementById('btn-toggle-role-inline-edit');
  if (btnToggleRoleEdit) btnToggleRoleEdit.addEventListener('click', () => window.antApp.toggleRoleInlineEdit());
  const btnSaveRoleInline = document.getElementById('btn-save-role-inline');
  if (btnSaveRoleInline) btnSaveRoleInline.addEventListener('click', () => window.antApp.saveRoleInline());
  const btnAddRoleModal = document.getElementById('btn-add-role-modal');
  if (btnAddRoleModal) btnAddRoleModal.addEventListener('click', () => window.antApp.addCustomRoleModal());
  const btnEditRoleInSkillEditor = document.getElementById('btn-edit-role-in-skill-editor');
  if (btnEditRoleInSkillEditor) btnEditRoleInSkillEditor.addEventListener('click', () => {
    if (window.antApp.activeSelectedRole) {
      window.antApp.closeRolesModal();
      openSkillEditor(window.antApp.activeSelectedRole.md_file);
    }
  });

  // Skill Editor
  const btnOpenSkillEditorEl = document.getElementById('btn-open-skill-editor');
  if (btnOpenSkillEditorEl) btnOpenSkillEditorEl.addEventListener('click', () => openSkillEditor());
  const btnCloseSkillEditor = document.getElementById('btn-close-skill-editor');
  if (btnCloseSkillEditor) btnCloseSkillEditor.addEventListener('click', () => {
    document.getElementById('modal-skill-editor').classList.add('hidden');
  });
    const btnDeleteSkill = document.getElementById('btn-delete-skill');
  if (btnDeleteSkill) btnDeleteSkill.addEventListener('click', () => deleteSkillFile());
  const btnDeleteMd = document.getElementById('btn-delete-md');
  if (btnDeleteMd) btnDeleteMd.addEventListener('click', () => deleteMdFile());
  const btnSaveSkill = document.getElementById('btn-save-skill');
  if (btnSaveSkill) btnSaveSkill.addEventListener('click', () => saveSkillFile());
  const btnCreateNewSkill = document.getElementById('btn-create-new-skill');
  if (btnCreateNewSkill) btnCreateNewSkill.addEventListener('click', () => createNewSkillFile());

  // MD Editor
  const btnOpenMdEditorEl = document.getElementById('btn-open-md-editor');
  if (btnOpenMdEditorEl) btnOpenMdEditorEl.addEventListener('click', () => openMdEditor());
  const btnCloseMdEditor = document.getElementById('btn-close-md-editor');
  if (btnCloseMdEditor) btnCloseMdEditor.addEventListener('click', () => {
    document.getElementById('modal-md-editor').classList.add('hidden');
  });
  const btnSaveMd = document.getElementById('btn-save-md');
  if (btnSaveMd) btnSaveMd.addEventListener('click', () => saveMdFile());
  const btnCreateNewMd = document.getElementById('btn-create-new-md');
  if (btnCreateNewMd) btnCreateNewMd.addEventListener('click', () => createNewMdFile());
});


// Anti-Inspect and Code Protection Guard
(function() {
  // 1. Disable context menu (right click)
  document.addEventListener('contextmenu', function(e) {
    e.preventDefault();
    return false;
  }, { capture: true });

  // 2. Intercept DevTools and View Source Shortcuts
  document.addEventListener('keydown', function(e) {
    const isCtrlOrCmd = e.ctrlKey || e.metaKey;
    const key = e.key ? e.key.toLowerCase() : '';
    
    // F12, Ctrl+U, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C
    if (
      e.key === 'F12' ||
      (isCtrlOrCmd && key === 'u') ||
      (isCtrlOrCmd && e.shiftKey && (key === 'i' || key === 'j' || key === 'c'))
    ) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }
  }, { capture: true });
})();

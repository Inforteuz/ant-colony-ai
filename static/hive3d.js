/**
 * Ant Colony AI Platform — Full 3D Interactive Cyber-Hive & Virtual AI Office
 * Built with Three.js (r128)
 * 
 * Features:
 * - 7 3D Workstations (PM Command Bridge, Developer, QA Tester, Security Auditor, Designer, DevOps, Data Analyst)
 * - 3D Animated AI Agent Avatars:
 *   - Autonomous corridor roaming & patrolling when idle
 *   - Real-time walking to designated workstation when task is assigned
 *   - Smooth sit-down animation into workstation chair
 *   - Rapid procedural keyboard typing & monitor focus while coding/testing/auditing
 *   - Standing up, celebration victory animations upon completion
 * - Animated Canvas Textures on 3D Monitors
 * - 3D Holographic Status Badges with sharp Dark & Light theme rendering
 * - Camera Controls: Orbit, Pan, Zoom, and Quick-View Presets
 * - Full Dynamic Dark & Light Theme studio lighting & materials support
 */

class IsometricHive3D {
  constructor(containerId, canvasId) {
    this.container = document.getElementById(containerId);
    this.canvas = document.getElementById(canvasId);
    if (!this.container || !this.canvas) return;

    this.isLight = document.body.classList.contains('light-theme') || (localStorage.getItem('ant_theme') === 'light');

    this.stations = [
      { id: 'pm', name: 'Центральное управление (PM)', sub: 'DeepSeek V4 Flash', roleId: 'pm_orchestrator', color: '#8b5cf6', colorHex: 0x8b5cf6, pos: { x: 0, y: 0, z: 0 }, chairPos: { x: 0, y: 0, z: 2.1 }, deskPos: { x: 0, y: 0, z: 0.8 }, active: true, action: 'Оркестратор активен' },
      { id: 'coder', name: 'Инженер-разработчик', sub: 'DeepSeek V4 Flash', roleId: 'frontend_architect', color: '#6366f1', colorHex: 0x6366f1, pos: { x: -8.5, y: 0, z: 3.5 }, chairPos: { x: -8.5, y: 0, z: 5.4 }, deskPos: { x: -8.5, y: 0, z: 4.2 }, active: false, action: '' },
      { id: 'designer', name: 'Дизайнер UI/UX', sub: 'DeepSeek V4 Flash', roleId: 'ui_ux_designer', color: '#ec4899', colorHex: 0xec4899, pos: { x: -10.5, y: 0, z: -4.5 }, chairPos: { x: -10.5, y: 0, z: -2.6 }, deskPos: { x: -10.5, y: 0, z: -3.8 }, active: false, action: '' },
      { id: 'tester', name: 'Инженер тестирования (QA)', sub: 'Nemotron 3.5', roleId: 'qa_test_automation', color: '#06b6d4', colorHex: 0x06b6d4, pos: { x: -3.5, y: 0, z: 9.0 }, chairPos: { x: -3.5, y: 0, z: 10.9 }, deskPos: { x: -3.5, y: 0, z: 9.7 }, active: false, action: '' },
      { id: 'monitor', name: 'Аудит безопасности', sub: 'Nemotron 3.5', roleId: 'security_auditor', color: '#f43f5e', colorHex: 0xf43f5e, pos: { x: 8.5, y: 0, z: 3.5 }, chairPos: { x: 8.5, y: 0, z: 5.4 }, deskPos: { x: 8.5, y: 0, z: 4.2 }, active: false, action: '' },
      { id: 'researcher', name: 'Аналитик данных', sub: 'Gemini 2.5 Flash', roleId: 'data_engineer', color: '#10b981', colorHex: 0x10b981, pos: { x: 10.5, y: 0, z: -4.5 }, chairPos: { x: 10.5, y: 0, z: -2.6 }, deskPos: { x: 10.5, y: 0, z: -3.8 }, active: false, action: '' },
      { id: 'deployer', name: 'Инженер DevOps', sub: 'Hy3 Faster', roleId: 'devops_deployer', color: '#f97316', colorHex: 0xf97316, pos: { x: 3.5, y: 0, z: -9.0 }, chairPos: { x: 3.5, y: 0, z: -7.1 }, deskPos: { x: 3.5, y: 0, z: -8.3 }, active: false, action: '' }
    ];

    this.activeStation = 'pm';
    this.agents = {};
    this.stationObjects = {};
    this.particles = [];
    this.beamCurves = [];
    this.clock = new THREE.Clock();

    // Camera preset targets for smooth tweening
    this.cameraPresets = {
      overview: { pos: new THREE.Vector3(0, 20, 22), target: new THREE.Vector3(0, 0, 0) },
      pm: { pos: new THREE.Vector3(0, 6, 8.5), target: new THREE.Vector3(0, 1.2, 0.5) },
      coder: { pos: new THREE.Vector3(-8.5, 5, 10.5), target: new THREE.Vector3(-8.5, 1.2, 4.2) },
      designer: { pos: new THREE.Vector3(-10.5, 5, 2), target: new THREE.Vector3(-10.5, 1.2, -3.8) },
      tester: { pos: new THREE.Vector3(-3.5, 5, 15.5), target: new THREE.Vector3(-3.5, 1.2, 9.7) },
      monitor: { pos: new THREE.Vector3(8.5, 5, 10.5), target: new THREE.Vector3(8.5, 1.2, 4.2) },
      researcher: { pos: new THREE.Vector3(10.5, 5, 2), target: new THREE.Vector3(10.5, 1.2, -3.8) },
      deployer: { pos: new THREE.Vector3(3.5, 5, -2.5), target: new THREE.Vector3(3.5, 1.2, -8.3) },
      pingpong: { pos: new THREE.Vector3(22.0, 5.5, 23.5), target: new THREE.Vector3(22.0, 1.0, 16.0) },
      gym: { pos: new THREE.Vector3(-22.0, 5.5, -9.5), target: new THREE.Vector3(-22.0, 1.0, -16.0) },
      football: { pos: new THREE.Vector3(0, 9.5, -11.0), target: new THREE.Vector3(0, 0.8, -23.5) }
    };

    this.targetCameraPos = this.cameraPresets.overview.pos.clone();
    this.targetCameraLookAt = this.cameraPresets.overview.target.clone();

    this.initThree();
    this.createEnvironment();
    this.createWorkstations();
    this.createAgents();
    this.createPingPongArea();
    this.createGymArea();
    this.createFootballArea();
    this.createDataStreamSystem();
    this.setupInteractions();
    this.setupCameraControlsUI();

    this.restoreSwarmState();
    this.setRecreationVisibility();
    this.startIdleDialogueLoop();
    window.addEventListener('resize', () => this.onResize());
    this.animate();
    setInterval(() => this.saveSwarmState(), 2000);
  }

  initThree() {
    const w = this.container.clientWidth || window.innerWidth || 800;
    const h = this.container.clientHeight || window.innerHeight || 500;
    const isLight = this.isLight;
    const bgCol = isLight ? 0xf8fafc : 0x070b14;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(bgCol);
    this.scene.fog = new THREE.FogExp2(bgCol, isLight ? 0.012 : 0.022);

    this.camera = new THREE.PerspectiveCamera(42, w / h, 0.5, 1000);
    this.camera.position.copy(this.cameraPresets.overview.pos);

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance',
      alpha: false
    });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = isLight ? 1.35 : 1.15;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Adaptive quality — FPS ga qarab piksel ratio, soya va animatsiya throttle sozlanadi.
    // Foydalanuvchining zaif noutbukida ham 60 FPS ni ushlab turishga urinamiz.
    this.quality = {
      mode: 'high',        // 'high' | 'medium' | 'low'
      fpsHistory: [],
      lastCheck: performance.now(),
      framesInWindow: 0,
      windowMs: 1500,
      // Uzoq robotlarni har necha frame'da yangilash (1 = har frame'da).
      farSkipFrames: 1,
      farDistance: 22,
      frameIndex: 0,
      manuallySet: false,
    };

    if (window.THREE && window.THREE.OrbitControls) {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.06;
      this.controls.maxPolarAngle = Math.PI / 2.05;
      this.controls.minDistance = 4;
      this.controls.maxDistance = 50;
      this.controls.target.copy(this.cameraPresets.overview.target);
    }

    // High Key Studio Lighting
    this.ambientLight = new THREE.AmbientLight(0xffffff, isLight ? 1.4 : 0.7);
    this.scene.add(this.ambientLight);

    this.dirLight = new THREE.DirectionalLight(isLight ? 0xffffff : 0xdbeafe, isLight ? 1.8 : 1.2);
    this.dirLight.position.set(15, 30, 15);
    this.dirLight.castShadow = true;
    this.dirLight.shadow.mapSize.width = 1024;
    this.dirLight.shadow.mapSize.height = 1024;
    this.dirLight.shadow.bias = -0.0005;
    this.scene.add(this.dirLight);

    this.bluePoint = new THREE.PointLight(0x6366f1, isLight ? 1.2 : 2.0, 35);
    this.bluePoint.position.set(0, 8, 0);
    this.scene.add(this.bluePoint);
  }

  createEnvironment() {
    const isLight = this.isLight;

    // 1. Grid Floor
    const floorGeo = new THREE.PlaneGeometry(90, 90, 40, 40);
    this.floorMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0xf1f5f9 : 0x0c1322,
      roughness: isLight ? 0.35 : 0.25,
      metalness: isLight ? 0.15 : 0.75
    });
    const floor = new THREE.Mesh(floorGeo, this.floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.scene.add(floor);

    // 2. Grid Overlay
    this.gridHelper = new THREE.GridHelper(70, 35, isLight ? 0x6366f1 : 0x3b82f6, isLight ? 0xd1d5db : 0x1e293b);
    this.gridHelper.position.y = 0.01;
    this.scene.add(this.gridHelper);

    // 3. Central PM Command Platform (Raised Hexagon Core)
    const platGeo = new THREE.CylinderGeometry(4.2, 4.8, 0.35, 6);
    this.pmPlatMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0xffffff : 0x181e36,
      roughness: 0.3,
      metalness: isLight ? 0.2 : 0.85
    });
    const pmPlat = new THREE.Mesh(platGeo, this.pmPlatMat);
    pmPlat.position.set(0, 0.175, 0);
    pmPlat.receiveShadow = true;
    this.scene.add(pmPlat);

    // Glowing rim around central platform
    const rimGeo = new THREE.RingGeometry(4.2, 4.35, 6);
    const rimMat = new THREE.MeshBasicMaterial({ color: 0x8b5cf6, side: THREE.DoubleSide });
    const rim = new THREE.Mesh(rimGeo, rimMat);
    rim.rotation.x = -Math.PI / 2;
    rim.position.set(0, 0.36, 0);
    this.scene.add(rim);

    // 4. Ambient Floating Cyber Dust Particles
    const dustCount = 180;
    const dustGeo = new THREE.BufferGeometry();
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount * 3; i += 3) {
      dustPos[i] = (Math.random() - 0.5) * 45;
      dustPos[i + 1] = Math.random() * 12 + 0.5;
      dustPos[i + 2] = (Math.random() - 0.5) * 45;
    }
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({
      color: isLight ? 0x6366f1 : 0x818cf8,
      size: 0.14,
      transparent: true,
      opacity: isLight ? 0.4 : 0.6
    });
    this.dustParticles = new THREE.Points(dustGeo, dustMat);
    this.scene.add(this.dustParticles);
  }

  // --- Dynamic Canvas Textures for 3D Monitors ---
  createMonitorTexture(type, colorHex) {
    const cvs = document.createElement('canvas');
    cvs.width = 512;
    cvs.height = 256;
    const ctx = cvs.getContext('2d');

    const updateTexture = (time) => {
      const isLight = this.isLight;
      ctx.fillStyle = isLight ? '#0f172a' : '#060a12';
      ctx.fillRect(0, 0, 512, 256);

      // Window titlebar
      ctx.fillStyle = isLight ? '#1e293b' : '#101726';
      ctx.fillRect(0, 0, 512, 24);
      ctx.fillStyle = '#ef4444';
      ctx.beginPath(); ctx.arc(14, 12, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#f59e0b';
      ctx.beginPath(); ctx.arc(28, 12, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#10b981';
      ctx.beginPath(); ctx.arc(42, 12, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#94a3b8';
      ctx.font = 'bold 11px JetBrains Mono, monospace';
      ctx.fillText(`${type.toUpperCase()} :: AI AGENT TERMINAL`, 65, 16);

      // Live Scrolling Matrix/Code Lines
      ctx.font = '11px JetBrains Mono, monospace';
      const lines = [
        `import antigravity as agy`,
        `const orchestrator = new PMOrchestrator();`,
        `[OK] LLM Provider connected: OpenRouter / Groq`,
        `await agent.dispatchTask({ model: 'posiden/deepseek-v4' });`,
        `qa.runVerificationSuite({ coverage: '100%' });`,
        `>> SUCCESS: continuous_evaluation_score: 96/100`,
        `>> STREAMING TOKENS: ${(Math.sin(time*3)*150 + 400).toFixed(0)} t/s`
      ];

      for (let i = 0; i < lines.length; i++) {
        const offset = Math.floor((time * 4 + i) % lines.length);
        const y = 50 + i * 28;
        ctx.fillStyle = i === 0 ? colorHex : (i % 2 === 0 ? '#38bdf8' : '#94a3b8');
        ctx.fillText(lines[offset], 15, y);
      }

      // Neon bottom status pulse
      ctx.fillStyle = colorHex;
      const barW = Math.abs(Math.sin(time * 2)) * 480;
      ctx.fillRect(16, 240, barW, 4);
    };

    const texture = new THREE.CanvasTexture(cvs);
    texture.updateAnim = updateTexture;
    return texture;
  }

  // --- Workstations Creation ---
  createWorkstations() {
    this.stationObjects = {};
    const isLight = this.isLight;

    this.stations.forEach(st => {
      const group = new THREE.Group();
      group.position.set(st.pos.x, st.pos.y, st.pos.z);
      group.stationData = st;

      // 1. Station Floor Pedestal & Ring
      const ringGeo = new THREE.CylinderGeometry(2.6, 2.9, 0.12, 6);
      const pedestalMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0xffffff : 0x11192e,
        roughness: 0.35,
        metalness: isLight ? 0.2 : 0.8
      });
      const pedestal = new THREE.Mesh(ringGeo, pedestalMat);
      pedestal.position.y = 0.06;
      pedestal.receiveShadow = true;
      group.add(pedestal);
      group.pedestalMat = pedestalMat;

      // Glowing Station Accent Border
      const borderGeo = new THREE.RingGeometry(2.6, 2.75, 6);
      const borderMat = new THREE.MeshBasicMaterial({ color: st.colorHex, side: THREE.DoubleSide });
      const border = new THREE.Mesh(borderGeo, borderMat);
      border.rotation.x = -Math.PI / 2;
      border.position.y = 0.13;
      group.add(border);

      // 2. 3D Computer Desk (High-tech carbon table / Modern White Desk)
      const deskTopGeo = new THREE.BoxGeometry(2.4, 0.08, 1.1);
      const deskMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0xffffff : 0x1e293b,
        roughness: 0.2,
        metalness: isLight ? 0.1 : 0.8
      });
      const deskTop = new THREE.Mesh(deskTopGeo, deskMat);
      deskTop.position.set(0, 0.95, st.id === 'pm' ? 0.8 : (st.pos.z > 0 ? 0.7 : -0.7));
      deskTop.castShadow = true;
      deskTop.receiveShadow = true;
      group.add(deskTop);
      group.deskMat = deskMat;

      // Desk Legs
      const legGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.95, 8);
      const legMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0x94a3b8 : 0x0f172a,
        metalness: 0.9,
        roughness: 0.2
      });
      const legOffsets = [[-1.1, 0.45], [1.1, 0.45], [-1.1, -0.45], [1.1, -0.45]];
      legOffsets.forEach(([lx, lz]) => {
        const leg = new THREE.Mesh(legGeo, legMat);
        leg.position.set(lx, 0.475, deskTop.position.z + lz);
        leg.castShadow = true;
        group.add(leg);
      });

      // 3. Ergonomic Cyber Chair
      const chairGroup = new THREE.Group();
      chairGroup.position.set(0, 0, st.id === 'pm' ? 2.1 : (st.pos.z > 0 ? 1.9 : -1.9));
      if (st.pos.z < 0 && st.id !== 'pm') chairGroup.rotation.y = Math.PI;

      const seatGeo = new THREE.BoxGeometry(0.65, 0.08, 0.65);
      const chairMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0xe2e8f0 : 0x0f172a,
        roughness: 0.5
      });
      const seat = new THREE.Mesh(seatGeo, chairMat);
      seat.position.y = 0.55;
      chairGroup.add(seat);
      group.chairMat = chairMat;

      const backGeo = new THREE.BoxGeometry(0.6, 0.7, 0.08);
      const back = new THREE.Mesh(backGeo, chairMat);
      back.position.set(0, 0.95, 0.3);
      chairGroup.add(back);

      const chairLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.55, 8), legMat);
      chairLeg.position.y = 0.275;
      chairGroup.add(chairLeg);
      group.add(chairGroup);

      // 4. Multi-Monitor Setup with Live Code Textures
      const monTexture = this.createMonitorTexture(st.id, st.color);
      const monMat = new THREE.MeshBasicMaterial({ map: monTexture });
      const monScreenGeo = new THREE.BoxGeometry(1.2, 0.65, 0.04);
      const screen = new THREE.Mesh(monScreenGeo, monMat);
      screen.position.set(0, 1.4, deskTop.position.z);
      if (st.pos.z < 0 && st.id !== 'pm') screen.rotation.y = Math.PI;
      group.add(screen);
      group.monitorTexture = monTexture;

      // Keyboard & RGB Mat
      const kbGeo = new THREE.BoxGeometry(0.7, 0.02, 0.25);
      const kbMat = new THREE.MeshStandardMaterial({ color: 0x020617, roughness: 0.3 });
      const kb = new THREE.Mesh(kbGeo, kbMat);
      kb.position.set(0, 1.0, deskTop.position.z + (st.pos.z > 0 || st.id === 'pm' ? 0.25 : -0.25));
      group.add(kb);

      // 5. Overhead Floating Holographic 3D Badge
      const badge = this.createHolographicBadge(st.name, st.sub, st.color);
      badge.position.set(0, 2.5, 0);
      group.add(badge);
      group.badge = badge;

      // Station PointLight for realistic local glow
      const pLight = new THREE.PointLight(st.colorHex, 0.8, 6);
      pLight.position.set(0, 1.5, deskTop.position.z);
      group.add(pLight);
      group.pointLight = pLight;

      this.scene.add(group);
      this.stationObjects[st.id] = group;
    });

    // Central Floating Holographic Core for PM
    const coreGeo = new THREE.IcosahedronGeometry(0.75, 1);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x8b5cf6,
      emissive: 0x6d28d9,
      wireframe: true,
      roughness: 0.1
    });
    this.centralCore = new THREE.Mesh(coreGeo, coreMat);
    this.centralCore.position.set(0, 1.8, 0);
    this.scene.add(this.centralCore);
  }

  // --- Overhead Holographic 3D Billboard Badge ---
  createHolographicBadge(title, model, colorHex) {
    const cvs = document.createElement('canvas');
    cvs.width = 640;
    cvs.height = 200;
    const ctx = cvs.getContext('2d');

    const texture = new THREE.CanvasTexture(cvs);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;

    let currentTitle = title;
    let currentModel = model;

    const redraw = (actionText = '', newTitle = null, newModel = null) => {
      if (newTitle) currentTitle = newTitle;
      if (newModel) currentModel = newModel;

      ctx.clearRect(0, 0, 640, 200);

      const isLight = Boolean(this.isLight);
      const isActive = Boolean(actionText && actionText !== 'В ожидании');

      // Glassmorphic background container
      if (isLight) {
        ctx.fillStyle = isActive ? 'rgba(255, 255, 255, 0.98)' : 'rgba(248, 250, 252, 0.94)';
        ctx.strokeStyle = isActive ? colorHex : 'rgba(203, 213, 225, 0.9)';
        ctx.lineWidth = isActive ? 5 : 3;
      } else {
        ctx.fillStyle = isActive ? 'rgba(10, 20, 40, 0.94)' : 'rgba(11, 17, 30, 0.85)';
        ctx.strokeStyle = isActive ? colorHex : 'rgba(100, 116, 139, 0.4)';
        ctx.lineWidth = isActive ? 5 : 3;
      }

      ctx.beginPath();
      ctx.roundRect(8, 8, 624, 184, 24);
      ctx.fill();
      ctx.stroke();

      // Top glowing bar
      ctx.fillStyle = colorHex;
      ctx.beginPath();
      ctx.roundRect(24, 14, 592, 4, 2);
      ctx.fill();

      // Role title
      ctx.fillStyle = isLight ? '#0f172a' : '#ffffff';
      ctx.font = 'bold 30px Plus Jakarta Sans, sans-serif';
      ctx.fillText(currentTitle, 32, 60);

      // Model Tag
      ctx.fillStyle = colorHex;
      ctx.font = 'bold 22px JetBrains Mono, monospace';
      ctx.fillText(`• ${currentModel}`, 32, 100);

      // Live Action State
      const displayAction = actionText || 'В ожидании';
      if (isLight) {
        ctx.fillStyle = isActive ? '#2563eb' : '#64748b';
      } else {
        ctx.fillStyle = isActive ? '#38bdf8' : '#94a3b8';
      }
      ctx.font = 'bold 22px Plus Jakarta Sans, sans-serif';
      ctx.fillText(isActive ? `▶ ${displayAction.slice(0, 36)}` : `● ${displayAction}`, 32, 150);

      texture.needsUpdate = true;
    };

    redraw();

    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(3.8, 1.2, 1.0);
    sprite.redraw = redraw;
    return sprite;
  }

  // --- Procedural High-Detail Cybernetic AI Android Avatar Builder ---
  createAgentMesh(roleColorHex) {
    const agent = new THREE.Group();
    const isLight = this.isLight;

    // Premium Materials
    const armorMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0x1e293b : 0xf8fafc,
      roughness: isLight ? 0.3 : 0.18,
      metalness: isLight ? 0.6 : 0.35
    });

    const jointMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0x64748b : 0x334155,
      roughness: 0.2,
      metalness: 0.9
    });

    const glowMat = new THREE.MeshStandardMaterial({
      color: roleColorHex,
      emissive: roleColorHex,
      emissiveIntensity: 1.4,
      roughness: 0.1
    });

    // 1. Root Body Group (Upper Torso, Spine, Head & Arms)
    const bodyGroup = new THREE.Group();
    bodyGroup.position.y = 0.95;

    // --- Upper Torso (Athletic Sculpted V-Shape Chest) ---
    const chestGeo = new THREE.CylinderGeometry(0.24, 0.18, 0.34, 16);
    chestGeo.scale(1.2, 1.0, 0.7);
    const chest = new THREE.Mesh(chestGeo, armorMat);
    chest.position.y = 0.14;
    chest.castShadow = true;
    bodyGroup.add(chest);

    // Glowing Arc Reactor Chest Core
    const coreGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.03, 16);
    coreGeo.rotateX(Math.PI / 2);
    const core = new THREE.Mesh(coreGeo, glowMat);
    core.position.set(0, 0.18, 0.12);
    bodyGroup.add(core);

    const coreRingGeo = new THREE.TorusGeometry(0.075, 0.012, 8, 20);
    const coreRing = new THREE.Mesh(coreRingGeo, jointMat);
    coreRing.position.set(0, 0.18, 0.125);
    bodyGroup.add(coreRing);

    // --- Mid-Spine & Abdomen (Mechanical Ribs) ---
    const spineGeo = new THREE.CylinderGeometry(0.13, 0.15, 0.14, 12);
    const spine = new THREE.Mesh(spineGeo, jointMat);
    spine.position.y = -0.10;
    bodyGroup.add(spine);

    // Pelvis Chassis
    const pelvisGeo = new THREE.CylinderGeometry(0.16, 0.14, 0.12, 12);
    pelvisGeo.scale(1.15, 1.0, 0.75);
    const pelvis = new THREE.Mesh(pelvisGeo, armorMat);
    pelvis.position.y = -0.22;
    pelvis.castShadow = true;
    bodyGroup.add(pelvis);

    // --- 2. Head & Futuristic Curved Helmet ---
    const headGroup = new THREE.Group();
    headGroup.position.set(0, 0.44, 0);

    // Neck Joint
    const neckGeo = new THREE.CylinderGeometry(0.06, 0.07, 0.08, 12);
    const neck = new THREE.Mesh(neckGeo, jointMat);
    neck.position.y = -0.06;
    headGroup.add(neck);

    // Sculpted Helmet (Rounded Streamlined Capsule)
    const helmetGeo = new THREE.SphereGeometry(0.16, 16, 16);
    helmetGeo.scale(0.9, 1.05, 1.05);
    const helmet = new THREE.Mesh(helmetGeo, armorMat);
    helmet.position.y = 0.08;
    helmet.castShadow = true;
    headGroup.add(helmet);

    // Aerodynamic Curved Panoramic Visor
    const visorGeo = new THREE.CylinderGeometry(0.155, 0.155, 0.09, 16, 1, false, -Math.PI * 0.35, Math.PI * 0.7);
    visorGeo.rotateY(Math.PI / 2);
    const visor = new THREE.Mesh(visorGeo, glowMat);
    visor.position.set(0, 0.08, 0.04);
    headGroup.add(visor);

    // Ear Comms / Audio Sensor Pods
    const earGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.04, 12);
    earGeo.rotateZ(Math.PI / 2);
    const earL = new THREE.Mesh(earGeo, jointMat); earL.position.set(-0.16, 0.08, 0); headGroup.add(earL);
    const earR = new THREE.Mesh(earGeo, jointMat); earR.position.set(0.16, 0.08, 0); headGroup.add(earR);

    // LED Status Dot on Helmet Crown
    const ledGeo = new THREE.SphereGeometry(0.02, 8, 8);
    const led = new THREE.Mesh(ledGeo, glowMat);
    led.position.set(0, 0.24, -0.02);
    headGroup.add(led);

    bodyGroup.add(headGroup);

    // --- 3. Arms with Articulated Shoulder Pauldrons ---
    const buildArm = (isLeft) => {
      const armRoot = new THREE.Group();
      const side = isLeft ? -1 : 1;
      armRoot.position.set(side * 0.28, 0.22, 0);

      // Curved Shoulder Pauldron
      const pldGeo = new THREE.SphereGeometry(0.085, 12, 12, 0, Math.PI * 2, 0, Math.PI * 0.6);
      const pld = new THREE.Mesh(pldGeo, armorMat);
      pld.position.set(0, 0.02, 0);
      pld.castShadow = true;
      armRoot.add(pld);

      // Upper Arm (Bicep)
      const bicepGeo = new THREE.CylinderGeometry(0.048, 0.042, 0.18, 12);
      const bicep = new THREE.Mesh(bicepGeo, armorMat);
      bicep.position.y = -0.09;
      bicep.castShadow = true;
      armRoot.add(bicep);

      // Elbow Joint Sphere
      const elbowGeo = new THREE.SphereGeometry(0.04, 10, 10);
      const elbow = new THREE.Mesh(elbowGeo, jointMat);
      elbow.position.y = -0.20;
      armRoot.add(elbow);

      // Forearm with Neon Circuit Stripe
      const forearmGeo = new THREE.CylinderGeometry(0.042, 0.036, 0.18, 12);
      const forearm = new THREE.Mesh(forearmGeo, armorMat);
      forearm.position.y = -0.31;
      forearm.castShadow = true;
      armRoot.add(forearm);

      // Glowing circuit line on forearm
      const stripeGeo = new THREE.BoxGeometry(0.015, 0.12, 0.085);
      const stripe = new THREE.Mesh(stripeGeo, glowMat);
      stripe.position.set(0, -0.31, 0);
      armRoot.add(stripe);

      // Cyber Hand / Palm
      const handGeo = new THREE.BoxGeometry(0.05, 0.06, 0.04);
      const hand = new THREE.Mesh(handGeo, jointMat);
      hand.position.y = -0.42;
      hand.castShadow = true;
      armRoot.add(hand);

      return armRoot;
    };

    const leftArmGroup = buildArm(true);
    const rightArmGroup = buildArm(false);
    bodyGroup.add(leftArmGroup);
    bodyGroup.add(rightArmGroup);
    agent.add(bodyGroup);

    // --- 4. Legs with Articulated Knee Armor & Magnetic Boots ---
    const buildLeg = (isLeft) => {
      const legRoot = new THREE.Group();
      const side = isLeft ? -1 : 1;
      legRoot.position.set(side * 0.14, 0.65, 0);

      // Hip Joint
      const hipGeo = new THREE.SphereGeometry(0.05, 10, 10);
      const hip = new THREE.Mesh(hipGeo, jointMat);
      hip.position.y = 0;
      legRoot.add(hip);

      // Upper Leg (Thigh Armor)
      const thighGeo = new THREE.CylinderGeometry(0.065, 0.052, 0.26, 12);
      const thigh = new THREE.Mesh(thighGeo, armorMat);
      thigh.position.y = -0.14;
      thigh.castShadow = true;
      legRoot.add(thigh);

      // Knee Joint & Kneecap Armor
      const kneeGeo = new THREE.SphereGeometry(0.05, 10, 10);
      const knee = new THREE.Mesh(kneeGeo, jointMat);
      knee.position.y = -0.29;
      legRoot.add(knee);

      const kCapGeo = new THREE.BoxGeometry(0.06, 0.07, 0.04);
      const kCap = new THREE.Mesh(kCapGeo, glowMat);
      kCap.position.set(0, -0.29, 0.04);
      legRoot.add(kCap);

      // Shin / Calf Armor
      const shinGeo = new THREE.CylinderGeometry(0.052, 0.044, 0.26, 12);
      const shin = new THREE.Mesh(shinGeo, armorMat);
      shin.position.y = -0.44;
      shin.castShadow = true;
      legRoot.add(shin);

      // High-Tech Boot with Glowing Soles
      const bootGeo = new THREE.BoxGeometry(0.07, 0.06, 0.14);
      const boot = new THREE.Mesh(bootGeo, jointMat);
      boot.position.set(0, -0.59, 0.03);
      boot.castShadow = true;
      legRoot.add(boot);

      const soleGeo = new THREE.BoxGeometry(0.072, 0.015, 0.142);
      const sole = new THREE.Mesh(soleGeo, glowMat);
      sole.position.set(0, -0.625, 0.03);
      legRoot.add(sole);

      return legRoot;
    };

    const leftLegGroup = buildLeg(true);
    const rightLegGroup = buildLeg(false);
    agent.add(leftLegGroup);
    agent.add(rightLegGroup);

    // References for procedural animation & theme toggling
    agent.bodyGroup = bodyGroup;
    agent.headGroup = headGroup;
    agent.leftArmGroup = leftArmGroup;
    agent.rightArmGroup = rightArmGroup;
    agent.leftLegGroup = leftLegGroup;
    agent.rightLegGroup = rightLegGroup;
    agent.armorMat = armorMat;
    agent.jointMat = jointMat;
    agent.glowMat = glowMat;

    return agent;
  }

  // --- Create All 7 AI Agents ---
  createAgents() {
    this.agents = {};

    this.stations.forEach(st => {
      const mesh = this.createAgentMesh(st.colorHex);
      const chairPos = st.chairPos;
      mesh.position.set(chairPos.x, 0, chairPos.z);

      const agentData = {
        id: st.id,
        roleId: st.roleId,
        stationId: st.id,
        mesh: mesh,
        state: st.id === 'pm' ? 'WORKING' : 'IDLE_ROAM',
        targetPos: new THREE.Vector3(chairPos.x, 0, chairPos.z),
        walkSpeed: 3.2,
        animTime: Math.random() * 10,
        chairPos: new THREE.Vector3(chairPos.x, 0, chairPos.z),
        deskPos: new THREE.Vector3(st.deskPos.x, 0, st.deskPos.z),
        roamWaitTimer: Math.random() * 4 + 2
      };

      this.scene.add(mesh);
      this.agents[st.id] = agentData;
    });
  }


  createPingPongArea() {
    const isLight = this.isLight;
    const group = new THREE.Group();
    group.position.set(22.0, 0, 16.0);

    // 1. Lounge Floor Mat (Spacious Dual Court Lounge)
    const matGeo = new THREE.BoxGeometry(11.5, 0.06, 14.5);
    const matMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0xe2e8f0 : 0x0f172a,
      roughness: 0.4,
      metalness: isLight ? 0.1 : 0.6
    });
    const matMesh = new THREE.Mesh(matGeo, matMat);
    matMesh.position.y = 0.03;
    matMesh.receiveShadow = true;
    group.add(matMesh);

    // Glowing Neon Perimeter Border
    const borderGeo = new THREE.BoxGeometry(11.6, 0.08, 14.6);
    const borderMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, wireframe: true });
    const borderMesh = new THREE.Mesh(borderGeo, borderMat);
    borderMesh.position.y = 0.04;
    group.add(borderMesh);

    // Helper: Build a Table Tennis Table at local (posX, posZ)
    const buildTable = (posX, posZ, colorHex) => {
      const tGroup = new THREE.Group();
      tGroup.position.set(posX, 0, posZ);

      // Table Top (waist height y = 0.65)
      const tableTopGeo = new THREE.BoxGeometry(2.2, 0.08, 3.8);
      const tableMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        roughness: 0.25,
        metalness: 0.3
      });
      const tableTop = new THREE.Mesh(tableTopGeo, tableMat);
      tableTop.position.set(0, 0.65, 0);
      tableTop.castShadow = true;
      tableTop.receiveShadow = true;
      tGroup.add(tableTop);

      // Center Line
      const centerLine = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.082, 3.8), new THREE.MeshBasicMaterial({ color: 0xffffff }));
      centerLine.position.set(0, 0.651, 0);
      tGroup.add(centerLine);

      // Table Net
      const net = new THREE.Mesh(
        new THREE.BoxGeometry(2.4, 0.22, 0.02),
        new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5, transparent: true, opacity: 0.85 })
      );
      net.position.set(0, 0.76, 0);
      tGroup.add(net);

      // 4 Legs
      const legGeo = new THREE.CylinderGeometry(0.05, 0.05, 0.61, 8);
      const legMat = new THREE.MeshStandardMaterial({ color: isLight ? 0x64748b : 0x334155, metalness: 0.85 });
      const legPos = [[-0.9, 0.305, -1.6], [0.9, 0.305, -1.6], [-0.9, 0.305, 1.6], [0.9, 0.305, 1.6]];
      legPos.forEach(p => {
        const leg = new THREE.Mesh(legGeo, legMat);
        leg.position.set(p[0], p[1], p[2]);
        leg.castShadow = true;
        tGroup.add(leg);
      });

      return tGroup;
    };

    // Table 1 (Корт 1: Pro Match)
    group.add(buildTable(0, -3.8, isLight ? 0x0284c7 : 0x0369a1));
    // Table 2 (Корт 2: Challenger Match)
    group.add(buildTable(0, 3.8, isLight ? 0x059669 : 0x047857));

    // 2 Ping Pong Balls
    const ballMat1 = new THREE.MeshStandardMaterial({ color: 0xffedd5, emissive: 0xf97316, emissiveIntensity: 1.2 });
    this.pingPongBall1 = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 12), ballMat1);
    this.pingPongBall1.position.set(0, 0.75, -3.8);
    group.add(this.pingPongBall1);

    const ballMat2 = new THREE.MeshStandardMaterial({ color: 0xffedd5, emissive: 0x10b981, emissiveIntensity: 1.2 });
    this.pingPongBall2 = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 12), ballMat2);
    this.pingPongBall2.position.set(0, 0.75, 3.8);
    group.add(this.pingPongBall2);

    // 3. Spectator Couch (Диван для очереди и зрителей)
    const couchGroup = new THREE.Group();
    couchGroup.position.set(-4.2, 0.08, 0);

    const seatGeo = new THREE.BoxGeometry(1.4, 0.35, 4.2);
    const couchMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0x475569 : 0x1e293b,
      roughness: 0.5,
      metalness: 0.2
    });
    const seat = new THREE.Mesh(seatGeo, couchMat);
    seat.position.y = 0.18;
    couchGroup.add(seat);

    const backGeo = new THREE.BoxGeometry(0.3, 0.5, 4.2);
    const back = new THREE.Mesh(backGeo, couchMat);
    back.position.set(-0.55, 0.5, 0);
    couchGroup.add(back);
    group.add(couchGroup);

    // 4. Match Physics & Finite 11-point Game Rules
    this.pingPongCourt1 = {
      side: 1,
      duration: 0.62,
      progress: 0,
      arcHeight: 0.42,
      scoreA: 5,
      scoreB: 4,
      playerAName: 'Разработчик',
      playerBName: 'QA Инженер',
      matchOver: false,
      winner: ''
    };

    this.pingPongCourt2 = {
      side: 1,
      duration: 0.68,
      progress: 0,
      arcHeight: 0.42,
      scoreA: 3,
      scoreB: 2,
      playerAName: 'DevOps',
      playerBName: 'Дизайнер',
      matchOver: false,
      winner: ''
    };

    // 5. Floating Scoreboard Billboard (Dual Match Tracking)
    const scoreCvs = document.createElement('canvas');
    scoreCvs.width = 512;
    scoreCvs.height = 180;
    this.pingPongScoreCvs = scoreCvs;
    this.pingPongScoreCtx = scoreCvs.getContext('2d');
    this.pingPongScoreTex = new THREE.CanvasTexture(scoreCvs);

    const scoreMat = new THREE.SpriteMaterial({ map: this.pingPongScoreTex, transparent: true });
    this.pingPongScoreboard = new THREE.Sprite(scoreMat);
    this.pingPongScoreboard.position.set(0, 2.6, 0);
    this.pingPongScoreboard.scale.set(4.6, 1.6, 1);
    group.add(this.pingPongScoreboard);

    this.redrawPingPongScoreboard();

    this.scene.add(group);
    this.pingPongGroup = group;
  }

  redrawPingPongScoreboard() {
    if (!this.pingPongScoreCtx) return;
    const ctx = this.pingPongScoreCtx;
    const isLight = this.isLight;
    const c1 = this.pingPongCourt1;
    const c2 = this.pingPongCourt2;

    ctx.clearRect(0, 0, 512, 180);

    // Glass Background Card
    ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.94)' : 'rgba(10, 15, 30, 0.92)';
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(8, 8, 496, 164, 20);
    ctx.fill();
    ctx.stroke();

    // Top Header
    ctx.fillStyle = '#06b6d4';
    ctx.font = 'bold 20px Plus Jakarta Sans, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('ТУРНИР ПО НАСТОЛЬНОМУ ТЕННИСУ (ДО 11 ОЧКОВ)', 256, 36);

    // Court 1 Status
    ctx.fillStyle = isLight ? '#0f172a' : '#ffffff';
    ctx.font = 'bold 22px JetBrains Mono, monospace';
    const c1Status = c1.matchOver ? `Победа: ${c1.winner} (${c1.scoreA}:${c1.scoreB})` : `Стол 1: ${c1.playerAName}  ${c1.scoreA} : ${c1.scoreB}  ${c1.playerBName}`;
    ctx.fillText(c1Status, 256, 76);

    // Court 2 Status
    ctx.fillStyle = isLight ? '#047857' : '#34d399';
    const c2Status = c2.matchOver ? `Победа: ${c2.winner} (${c2.scoreA}:${c2.scoreB})` : `Стол 2: ${c2.playerAName}  ${c2.scoreA} : ${c2.scoreB}  ${c2.playerBName}`;
    ctx.fillText(c2Status, 256, 114);

    // Sub Status
    ctx.fillStyle = isLight ? '#64748b' : '#94a3b8';
    ctx.font = '600 16px Plus Jakarta Sans, sans-serif';
    ctx.fillText('Свободные специалисты ожидают на диване очереди', 256, 150);

    this.pingPongScoreTex.needsUpdate = true;
  }

  createGymArea() {
    const isLight = this.isLight;
    const group = new THREE.Group();
    group.position.set(-22.0, 0, -16.0);

    // 1. Floor Platform (Large Hex Deck)
    const padGeo = new THREE.CylinderGeometry(6.2, 6.5, 0.08, 6);
    const padMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0xe2e8f0 : 0x0f172a,
      roughness: 0.35,
      metalness: isLight ? 0.1 : 0.7
    });
    const pad = new THREE.Mesh(padGeo, padMat);
    pad.position.y = 0.04;
    pad.receiveShadow = true;
    group.add(pad);

    // Glowing Neon Hex Perimeter
    const rimGeo = new THREE.RingGeometry(6.2, 6.35, 6);
    const rimMat = new THREE.MeshBasicMaterial({ color: 0x10b981, side: THREE.DoubleSide });
    const rim = new THREE.Mesh(rimGeo, rimMat);
    rim.rotation.x = -Math.PI / 2;
    rim.position.set(0, 0.09, 0);
    group.add(rim);

    // 2. Equipment 1 & 2: Dual Cyber Treadmills (Беговые дорожки)
    const createTreadmill = (posX, posZ) => {
      const tmGroup = new THREE.Group();
      tmGroup.position.set(posX, 0.08, posZ);

      // Treadmill Base
      const baseGeo = new THREE.BoxGeometry(1.2, 0.16, 2.2);
      const baseMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0x334155 : 0x1e293b,
        metalness: 0.8,
        roughness: 0.2
      });
      const base = new THREE.Mesh(baseGeo, baseMat);
      base.position.y = 0.08;
      base.castShadow = true;
      tmGroup.add(base);

      // Running Belt with glowing track lines
      const beltGeo = new THREE.BoxGeometry(0.85, 0.02, 1.8);
      const beltMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0x0f172a : 0x090d16,
        roughness: 0.8
      });
      const belt = new THREE.Mesh(beltGeo, beltMat);
      belt.position.set(0, 0.17, 0);
      tmGroup.add(belt);

      // Handrails & Upright Posts
      const railGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.9, 8);
      const railMat = new THREE.MeshStandardMaterial({ color: isLight ? 0x94a3b8 : 0x475569, metalness: 0.9 });
      const postL = new THREE.Mesh(railGeo, railMat); postL.position.set(-0.5, 0.55, -0.6); postL.castShadow = true; tmGroup.add(postL);
      const postR = new THREE.Mesh(railGeo, railMat); postR.position.set(0.5, 0.55, -0.6); postR.castShadow = true; tmGroup.add(postR);

      // Console Display Screen
      const screenGeo = new THREE.BoxGeometry(0.7, 0.35, 0.05);
      const screenMat = new THREE.MeshStandardMaterial({
        color: 0x06b6d4,
        emissive: 0x06b6d4,
        emissiveIntensity: 0.6
      });
      const screen = new THREE.Mesh(screenGeo, screenMat);
      screen.position.set(0, 1.05, -0.6);
      screen.rotation.x = 0.3;
      tmGroup.add(screen);

      return tmGroup;
    };

    group.add(createTreadmill(-2.4, -1.4)); // Treadmill 1
    group.add(createTreadmill(-2.4, 1.4));  // Treadmill 2

    // 3. Equipment 3: Holographic Boxing / Sparring Pod (Силовой спарринг)
    const boxGroup = new THREE.Group();
    boxGroup.position.set(2.0, 0.08, -1.5);
    
    // Stand
    const standGeo = new THREE.CylinderGeometry(0.4, 0.5, 0.15, 12);
    const standMat = new THREE.MeshStandardMaterial({ color: isLight ? 0x475569 : 0x1e293b, metalness: 0.8 });
    const stand = new THREE.Mesh(standGeo, standMat);
    stand.position.y = 0.075;
    boxGroup.add(stand);

    const poleGeo = new THREE.CylinderGeometry(0.05, 0.05, 1.5, 8);
    const pole = new THREE.Mesh(poleGeo, standMat);
    pole.position.y = 0.85;
    boxGroup.add(pole);

    // Floating Energy Punching Cylinder
    const bagGeo = new THREE.CylinderGeometry(0.32, 0.32, 1.0, 16);
    const bagMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0xef4444,
      emissiveIntensity: 0.7,
      roughness: 0.2
    });
    this.gymPunchingBag = new THREE.Mesh(bagGeo, bagMat);
    this.gymPunchingBag.position.set(0, 1.35, 0);
    this.gymPunchingBag.castShadow = true;
    boxGroup.add(this.gymPunchingBag);

    // Energy Shield Rings
    const shieldGeo = new THREE.TorusGeometry(0.5, 0.02, 8, 24);
    const shieldMat = new THREE.MeshBasicMaterial({ color: 0xf43f5e, transparent: true, opacity: 0.7 });
    const shield1 = new THREE.Mesh(shieldGeo, shieldMat); shield1.rotation.x = Math.PI / 2; shield1.position.y = 1.35; boxGroup.add(shield1);
    group.add(boxGroup);

    // 4. Equipment 4: Cyber Weightlifting Bench (Силовая скамья с штангой)
    const benchGroup = new THREE.Group();
    benchGroup.position.set(2.0, 0.08, 1.5);

    // Bench Pad
    const bPadGeo = new THREE.BoxGeometry(0.7, 0.1, 1.6);
    const bPadMat = new THREE.MeshStandardMaterial({ color: isLight ? 0x0284c7 : 0x0369a1, roughness: 0.3 });
    const bPad = new THREE.Mesh(bPadGeo, bPadMat);
    bPad.position.y = 0.35;
    bPad.castShadow = true;
    benchGroup.add(bPad);

    // Bench Legs
    const bLegGeo = new THREE.BoxGeometry(0.65, 0.3, 0.1);
    const bLegMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8 });
    const bLeg1 = new THREE.Mesh(bLegGeo, bLegMat); bLeg1.position.set(0, 0.15, -0.65); benchGroup.add(bLeg1);
    const bLeg2 = new THREE.Mesh(bLegGeo, bLegMat); bLeg2.position.set(0, 0.15, 0.65); benchGroup.add(bLeg2);

    // Barbell Rack & Barbell
    const rPostGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.9, 8);
    const rPost1 = new THREE.Mesh(rPostGeo, bLegMat); rPost1.position.set(-0.4, 0.45, -0.5); benchGroup.add(rPost1);
    const rPost2 = new THREE.Mesh(rPostGeo, bLegMat); rPost2.position.set(0.4, 0.45, -0.5); benchGroup.add(rPost2);

    // Barbell with Glowing Energy Discs
    const barGeo = new THREE.CylinderGeometry(0.025, 0.025, 1.2, 8);
    const bar = new THREE.Mesh(barGeo, bLegMat);
    bar.rotation.z = Math.PI / 2;
    bar.position.set(0, 0.92, -0.5);
    benchGroup.add(bar);

    const discGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.06, 12);
    const discMat = new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x10b981, emissiveIntensity: 0.8 });
    const disc1 = new THREE.Mesh(discGeo, discMat); disc1.rotation.z = Math.PI / 2; disc1.position.set(-0.55, 0.92, -0.5); benchGroup.add(disc1);
    const disc2 = new THREE.Mesh(discGeo, discMat); disc2.rotation.z = Math.PI / 2; disc2.position.set(0.55, 0.92, -0.5); benchGroup.add(disc2);
    group.add(benchGroup);

    // 5. Floating Gym Sign (Clean, No Emojis)
    const labelCvs = document.createElement('canvas');
    labelCvs.width = 440; labelCvs.height = 80;
    const lctx = labelCvs.getContext('2d');
    lctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.94)' : 'rgba(10, 25, 20, 0.92)';
    lctx.strokeStyle = '#10b981';
    lctx.lineWidth = 3;
    lctx.beginPath(); lctx.roundRect(8, 8, 424, 64, 16); lctx.fill(); lctx.stroke();

    lctx.fillStyle = '#10b981';
    lctx.font = 'bold 22px Plus Jakarta Sans, sans-serif';
    lctx.textAlign = 'center';
    lctx.fillText('ЗОНА РАЗМИНКИ И КАЛИБРОВКИ', 220, 48);

    const lTex = new THREE.CanvasTexture(labelCvs);
    const lSprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: lTex, transparent: true }));
    lSprite.position.set(0, 2.6, 0);
    lSprite.scale.set(4.0, 0.75, 1);
    group.add(lSprite);

    this.scene.add(group);
    this.gymGroup = group;
  }


  createFootballArea() {
    const isLight = this.isLight;
    const group = new THREE.Group();
    group.position.set(0, 0, -23.5);

    // 1. Emerald Green Pitch
    const pitchGeo = new THREE.BoxGeometry(13.0, 0.08, 17.0);
    const pitchMat = new THREE.MeshStandardMaterial({
      color: isLight ? 0x059669 : 0x064e3b,
      roughness: 0.5,
      metalness: 0.2
    });
    const pitch = new THREE.Mesh(pitchGeo, pitchMat);
    pitch.position.y = 0.04;
    pitch.receiveShadow = true;
    group.add(pitch);

    // White Boundary Lines
    const borderGeo = new THREE.BoxGeometry(13.1, 0.085, 17.1);
    const borderMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true });
    const border = new THREE.Mesh(borderGeo, borderMat);
    border.position.y = 0.045;
    group.add(border);

    // Center Line
    const centerLine = new THREE.Mesh(new THREE.BoxGeometry(13.0, 0.09, 0.06), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    centerLine.position.set(0, 0.05, 0);
    group.add(centerLine);

    // Center Circle
    const circleGeo = new THREE.RingGeometry(2.2, 2.28, 32);
    const circleMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
    const circle = new THREE.Mesh(circleGeo, circleMat);
    circle.rotation.x = -Math.PI / 2;
    circle.position.set(0, 0.09, 0);
    group.add(circle);

    // Penalty Area Box around North Goal
    const penBoxGeo = new THREE.BoxGeometry(7.0, 0.086, 4.0);
    const penBoxMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true });
    const penBox = new THREE.Mesh(penBoxGeo, penBoxMat);
    penBox.position.set(0, 0.05, -6.5);
    group.add(penBox);

    // 2. Goal Posts (North Goal at z = -7.5)
    const gGroup = new THREE.Group();
    gGroup.position.set(0, 0.08, -7.5);

    const postGeo = new THREE.CylinderGeometry(0.06, 0.06, 1.9, 8);
    const postMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2, metalness: 0.8 });

    // Uprights
    const p1 = new THREE.Mesh(postGeo, postMat); p1.position.set(-2.0, 0.95, 0); p1.castShadow = true; gGroup.add(p1);
    const p2 = new THREE.Mesh(postGeo, postMat); p2.position.set(2.0, 0.95, 0); p2.castShadow = true; gGroup.add(p2);

    // Crossbar
    const barGeo = new THREE.CylinderGeometry(0.06, 0.06, 4.0, 8);
    const bar = new THREE.Mesh(barGeo, postMat);
    bar.rotation.z = Math.PI / 2;
    bar.position.set(0, 1.9, 0);
    bar.castShadow = true;
    gGroup.add(bar);

    // Glowing Net
    const netGeo = new THREE.BoxGeometry(4.0, 1.9, 1.2);
    const netMat = new THREE.MeshStandardMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.45,
      wireframe: true
    });
    const net = new THREE.Mesh(netGeo, netMat);
    net.position.set(0, 0.95, -0.6);
    gGroup.add(net);
    group.add(gGroup);

    // 3. Floating Stadium Scoreboard Billboard (Elevated above goal at y = 4.2, z = -7.5 so it NEVER blocks the field!)
    const fbScoreCvs = document.createElement('canvas');
    fbScoreCvs.width = 800; fbScoreCvs.height = 180;
    this.footballScoreCvs = fbScoreCvs;
    this.footballScoreCtx = fbScoreCvs.getContext('2d');
    this.footballScoreTex = new THREE.CanvasTexture(fbScoreCvs);

    const fbScoreMat = new THREE.SpriteMaterial({ map: this.footballScoreTex, transparent: true });
    this.footballScoreboard = new THREE.Sprite(fbScoreMat);
    this.footballScoreboard.position.set(0, 4.2, -7.5);
    this.footballScoreboard.scale.set(6.4, 1.45, 1);
    group.add(this.footballScoreboard);

    this.scene.add(group);
    this.footballGroup = group;

    // 4. Cyber Football Ball
    const fbGeo = new THREE.SphereGeometry(0.20, 16, 16);
    const fbMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0x0ea5e9,
      emissiveIntensity: 0.9,
      roughness: 0.15,
      metalness: 0.3
    });
    this.footballBall = new THREE.Mesh(fbGeo, fbMat);
    this.footballBall.position.set(0, 0.24, -20.5);
    this.footballBall.castShadow = true;
    this.scene.add(this.footballBall);

    // Football Match State (Finite Best of 5 series)
    this.footballState = {
      active: true,
      time: 0,
      phase: 'RUN_UP',
      strikerName: 'Разработчик',
      keeperName: 'Дизайнер',
      scoreStriker: 2,
      scoreKeeper: 1,
      matchOver: false,
      winner: '',
      lastShotGoal: false,
      shotTargetX: 1.2
    };

    this.redrawFootballScoreboard();
  }

  redrawFootballScoreboard() {
    if (!this.footballScoreCtx) return;
    const ctx = this.footballScoreCtx;
    const isLight = this.isLight;
    const fb = this.footballState;

    ctx.clearRect(0, 0, 800, 180);

    // Glass Background Card
    ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(6, 25, 20, 0.94)';
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(8, 8, 784, 164, 20);
    ctx.fill();
    ctx.stroke();

    // Top Header
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 22px Plus Jakarta Sans, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('КИБЕР-ФУТБОЛ: СЕРИЯ ПЕНАЛЬТИ (ДО 5 ГОЛОВ)', 400, 40);

    // 3-Column Clean Layout: Striker (Left), Score (Center), Keeper (Right)
    const strName = this.getShortRoleName(fb.strikerName);
    const kpName = this.getShortRoleName(fb.keeperName);

    ctx.fillStyle = isLight ? '#0f172a' : '#ffffff';
    ctx.font = 'bold 24px Plus Jakarta Sans, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`${strName} (Удар)`, 36, 96);

    ctx.textAlign = 'right';
    ctx.fillText(`${kpName} (Вратарь)`, 764, 96);

    // Center Score Box
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 36px JetBrains Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`[ ${fb.scoreStriker} : ${fb.scoreKeeper} ]`, 400, 98);

    // Sub Status / Win Banner
    ctx.font = '600 18px Plus Jakarta Sans, sans-serif';
    if (fb.matchOver) {
      ctx.fillStyle = '#eab308';
      ctx.fillText(`🏆 ПОБЕДА: ${fb.winner}! Серия завершена (${fb.scoreStriker} - ${fb.scoreKeeper})`, 400, 145);
    } else {
      ctx.fillStyle = isLight ? '#059669' : '#34d399';
      const statusTxt = fb.lastShotGoal ? 'ГОЛ! Мяч в сетке ворот!' : 'Активная серия пенальти и ударов';
      ctx.fillText(statusTxt, 400, 145);
    }

    this.footballScoreTex.needsUpdate = true;
  }

  createDataStreamSystem() {
    this.beams = [];
    this.activeBeams = [];
  }

  emitDataPacket(fromStationId, toStationId, colorHex) {
    const fromSt = this.stations.find(s => s.id === fromStationId);
    const toSt = this.stations.find(s => s.id === toStationId);
    if (!fromSt || !toSt) return;

    const start = new THREE.Vector3(fromSt.pos.x, 1.4, fromSt.pos.z);
    const end = new THREE.Vector3(toSt.pos.x, 1.4, toSt.pos.z);
    const mid = new THREE.Vector3(
      (start.x + end.x) / 2,
      Math.max(start.y, end.y) + 3.5,
      (start.z + end.z) / 2
    );

    const curve = new THREE.QuadraticBezierCurve3(start, mid, end);

    const pGeo = new THREE.SphereGeometry(0.16, 8, 8);
    const pMat = new THREE.MeshBasicMaterial({ color: colorHex || 0x38bdf8 });
    const pMesh = new THREE.Mesh(pGeo, pMat);
    this.scene.add(pMesh);

    this.activeBeams.push({
      mesh: pMesh,
      curve: curve,
      progress: 0,
      speed: 0.85
    });
  }

  updateAgents(delta) {
    const time = this.clock.getElapsedTime();

    // LOD throttling: uzoq zonalarga qamera qaramayotgan bo'lsa, ular animatsiyasi
    // har `farSkipFrames` frame'da bir marta yangilanadi. FPS auto-manager buni
    // 1..3 orasida sozlaydi. Kamera zonaga yaqin bo'lsa yoki foydalanuvchi tarozni
    // sifat rejimida "high"da tutgan bo'lsa, hech qanday o'tkazib yuborish yo'q.
    const q = this.quality;
    const camPos = this.camera && this.camera.position;
    const dist = (x, y, z) => {
      if (!camPos) return 0;
      const dx = camPos.x - x, dy = camPos.y - y, dz = camPos.z - z;
      return Math.sqrt(dx*dx + dy*dy + dz*dz);
    };
    const skipTick = (zoneDist) => {
      if (!q || q.farSkipFrames <= 1) return false;
      if (zoneDist < q.farDistance) return false;
      return (q.frameIndex % q.farSkipFrames) !== 0;
    };
    const _pingPongDist = dist(22.0, 1.0, 16.0);
    const _footballDist = dist(0, 0.8, -20.0);
    const _gymDist = dist(-22.0, 1.0, -16.0);
    const _doPingPong = !skipTick(_pingPongDist);
    const _doFootball = !skipTick(_footballDist);
    const _doGym = !skipTick(_gymDist);

    // =============================================================
    // 1. PING PONG COURT 1: Player Presence Check & Realistic Physics
    // =============================================================
    const agT1_A = Object.values(this.agents).find(ag => ag.activityState === 'T1_A');
    const agT1_B = Object.values(this.agents).find(ag => ag.activityState === 'T1_B');
    const p1_ready = agT1_A && agT1_A.mesh.position.distanceTo(new THREE.Vector3(22.0, 0, 10.4)) < 0.8;
    const p2_ready = agT1_B && agT1_B.mesh.position.distanceTo(new THREE.Vector3(22.0, 0, 14.0)) < 0.8;

    if (_doPingPong && this.pingPongCourt1 && this.pingPongBall1) {
      const c1 = this.pingPongCourt1;

      if (p1_ready && p2_ready) {
        if (!c1.matchOver) {
          c1.progress += delta / c1.duration;
          if (c1.progress >= 1.0) {
            c1.progress = 0;
            c1.side *= -1;

            if (Math.random() < 0.16) {
              if (c1.side === 1) c1.scoreA++;
              else c1.scoreB++;

              if (c1.scoreA >= 11 || c1.scoreB >= 11) {
                c1.matchOver = true;
                c1.winner = c1.scoreA >= 11 ? c1.playerAName : c1.playerBName;
                setTimeout(() => {
                  c1.scoreA = 0; c1.scoreB = 0; c1.matchOver = false;
                  this.redrawPingPongScoreboard();
                }, 6000);
              }
              this.redrawPingPongScoreboard();
            }
          }

          const fromZ = c1.side === 1 ? -1.6 : 1.6;
          const toZ = c1.side === 1 ? 1.6 : -1.6;
          const curZ = -3.8 + THREE.MathUtils.lerp(fromZ, toZ, c1.progress);
          const arc = Math.sin(c1.progress * Math.PI) * c1.arcHeight;
          const bounce = Math.abs(Math.sin(c1.progress * Math.PI * 2)) * 0.12;
          this.pingPongBall1.position.set(Math.sin(c1.progress * Math.PI) * 0.25 * c1.side, 0.72 + arc + bounce, curZ);
        }
      } else if (p1_ready || p2_ready) {
        this.pingPongBall1.position.set(0, 0.72, p1_ready ? -4.6 : -3.0);
      } else {
        this.pingPongBall1.position.set(0, 0.72, -3.8);
      }
    }

    // =============================================================
    // 2. FOOTBALL ARENA: Realistic Multi-Stage Penalty Shootout!
    // =============================================================
    const agStriker = Object.values(this.agents).find(ag => ag.activityState === 'FB_STRIKER');
    const agKeeper = Object.values(this.agents).find(ag => ag.activityState === 'FB_KEEPER');
    const strikerReady = agStriker && agStriker.mesh.position.z <= -14.0;
    const keeperReady = agKeeper && agKeeper.mesh.position.distanceTo(new THREE.Vector3(0, 0, -30.8)) < 2.5;

    if (_doFootball && this.footballState && this.footballBall) {
      const fb = this.footballState;

      if (strikerReady && keeperReady) {
        fb.time += delta;
        const cycle = fb.time % 5.0; // 5.0s full penalty shootout sequence

        if (cycle < 1.6) {
          // Phase 1: Ball rests on spot at (0, 0.24, -20.5)
          this.footballBall.position.set(0, 0.24, -20.5);
          fb.lastShotGoal = false;
          // Randomize target side for this shot
          if (cycle < 0.1) fb.shotTargetX = (Math.random() - 0.5) * 2.8;
        } else if (cycle < 2.6) {
          // Phase 2: Ball launched towards North goal (z = -30.8) with height arc & spin
          const shotP = (cycle - 1.6) / 1.0;
          const curZ = THREE.MathUtils.lerp(-20.5, -30.8, shotP);
          const curX = THREE.MathUtils.lerp(0, fb.shotTargetX, shotP);
          const curY = 0.24 + Math.sin(shotP * Math.PI) * 1.5;
          this.footballBall.position.set(curX, curY, curZ);
          this.footballBall.rotation.x += delta * 18; // Fast spin

          if (shotP > 0.85 && !fb.lastShotGoal && !fb.matchOver) {
            fb.lastShotGoal = true;
            if (Math.random() < 0.65) fb.scoreStriker++;
            else fb.scoreKeeper++;

            // 5-goal finite match rule
            if (fb.scoreStriker >= 5 || fb.scoreKeeper >= 5) {
              fb.matchOver = true;
              fb.winner = fb.scoreStriker >= 5 ? this.getShortRoleName(fb.strikerName) : this.getShortRoleName(fb.keeperName);
              setTimeout(() => {
                fb.scoreStriker = 0;
                fb.scoreKeeper = 0;
                fb.matchOver = false;
                fb.winner = '';
                this.redrawFootballScoreboard();
              }, 6000);
            }
            this.redrawFootballScoreboard();
          }
        } else if (cycle < 4.6) {
          // Phase 3: Ball settled in goal net / ground
          this.footballBall.position.set(fb.shotTargetX * 0.8, 0.24, -30.8);
        } else {
          // Phase 4: Resetting
          this.footballBall.position.set(0, 0.24, -20.5);
        }
      } else {
        this.footballBall.position.set(0, 0.24, -20.5);
      }
    }

    // =============================================================
    // 3. Strict Non-Overlapping Slot Distribution for Idle Swarm
    // =============================================================
    const idleAgents = Object.values(this.agents).filter(ag => ag.state !== 'WORKING' && ag.state !== 'WALK_TO_DESK' && ag.state !== 'CELEBRATE');

    const EXCLUSIVE_SLOTS = [
      { state: 'FB_STRIKER', pos: new THREE.Vector3(0, 0, -15.5), label: 'Футбол: Нападающий' },
      { state: 'FB_KEEPER', pos: new THREE.Vector3(0, 0, -30.8), label: 'Футбол: Вратарь' },
      { state: 'T1_A', pos: new THREE.Vector3(22.0, 0, 10.4), label: 'Теннис: Игрок 1' },
      { state: 'T1_B', pos: new THREE.Vector3(22.0, 0, 14.0), label: 'Теннис: Игрок 2' },
      { state: 'GYM_TREAD', pos: new THREE.Vector3(-24.4, 0, -17.4), label: 'Фитнес: Беговая дорожка' },
      { state: 'GYM_BOXING', pos: new THREE.Vector3(-20.0, 0, -17.5), label: 'Фитнес: Спарринг-бокс' },
      { state: 'LOUNGE_QUEUE', pos: new THREE.Vector3(17.8, 0, 16.0), label: 'Зona отдыха: Диван' }
    ];

    idleAgents.forEach((ag, idx) => {
      const slot = EXCLUSIVE_SLOTS[idx % EXCLUSIVE_SLOTS.length];
      if (ag.activityState !== slot.state) {
        ag.activityState = slot.state;
        ag.activityLabel = slot.label;
        ag.targetPos.copy(slot.pos);
        ag.animTime = Math.random() * 5;

        // Assign player names on scoreboards
        const st = this.stations.find(s => s.id === ag.id);
        const name = st ? st.name.split(' ')[0] : ag.id;

        if (slot.state === 'T1_A') this.pingPongCourt1.playerAName = name;
        else if (slot.state === 'T1_B') this.pingPongCourt1.playerBName = name;
        else if (slot.state === 'FB_STRIKER') this.footballState.strikerName = name;
        else if (slot.state === 'FB_KEEPER') this.footballState.keeperName = name;
        this.redrawPingPongScoreboard();
        this.redrawFootballScoreboard();
      }
    });

    // =============================================================
    // 4. Update Overhead Workstation Badges with Live Agent Locations!
    // =============================================================
    this.stations.forEach(st => {
      const ag = this.agents[st.id];
      const stationObj = this.stationObjects[st.id];
      if (stationObj && stationObj.badge && stationObj.badge.redraw) {
        if (!ag || ag.state === 'WORKING') {
          stationObj.badge.redraw(st.action || 'В работе: Выполняет задачу', st.name, st.sub);
        } else if (ag.state === 'WALK_TO_DESK') {
          stationObj.badge.redraw('Идет на рабочее место', st.name, st.sub);
        } else {
          const locationDesc = ag.activityLabel || 'В зоне отдыха';
          stationObj.badge.redraw(`Вне места: ${locationDesc}`, st.name, st.sub);
        }
      }
    });

    // =============================================================
    // 5. Procedural Biomechanics & Dynamic Spatial Animations
    // =============================================================
    Object.values(this.agents).forEach(ag => {
      ag.animTime += delta;
      const mesh = ag.mesh;

      // WORKING (At Chair, Coding & Typing)
      if (ag.state === 'WORKING') {
        const targetDir = new THREE.Vector3().subVectors(ag.deskPos, ag.chairPos).normalize();
        mesh.rotation.y = Math.atan2(targetDir.x, targetDir.z);

        mesh.position.copy(ag.chairPos);
        mesh.bodyGroup.position.y = THREE.MathUtils.lerp(mesh.bodyGroup.position.y, 0.68, 0.15);
        mesh.leftLegGroup.rotation.x = THREE.MathUtils.lerp(mesh.leftLegGroup.rotation.x, -Math.PI / 2.2, 0.15);
        mesh.rightLegGroup.rotation.x = THREE.MathUtils.lerp(mesh.rightLegGroup.rotation.x, -Math.PI / 2.2, 0.15);

        const typeSpeed = ag.id === 'pm' ? 18 : 22;
        const typeL = Math.sin(ag.animTime * typeSpeed) * 0.14 - 0.75;
        const typeR = Math.cos(ag.animTime * typeSpeed) * 0.14 - 0.75;
        mesh.leftArmGroup.rotation.x = typeL;
        mesh.rightArmGroup.rotation.x = typeR;
        mesh.leftArmGroup.rotation.z = 0.22;
        mesh.rightArmGroup.rotation.z = -0.22;

        mesh.headGroup.rotation.y = Math.sin(ag.animTime * 3.2) * 0.32;
        mesh.headGroup.rotation.x = -0.15 + Math.cos(ag.animTime * 2.0) * 0.06;
      }

      // WALK_TO_DESK (Task Assigned -> Strides to Workstation)
      else if (ag.state === 'WALK_TO_DESK') {
        const dist = mesh.position.distanceTo(ag.chairPos);
        if (dist > 0.25) {
          const dir = new THREE.Vector3().subVectors(ag.chairPos, mesh.position).normalize();
          const targetAngle = Math.atan2(dir.x, dir.z);
          mesh.rotation.y = THREE.MathUtils.lerp(mesh.rotation.y, targetAngle, 0.14);
          mesh.position.addScaledVector(dir, ag.walkSpeed * 1.35 * delta);

          const walkCycle = Math.sin(ag.animTime * 10);
          mesh.leftLegGroup.rotation.x = walkCycle * 0.65;
          mesh.rightLegGroup.rotation.x = -walkCycle * 0.65;
          mesh.leftArmGroup.rotation.x = -walkCycle * 0.55;
          mesh.rightArmGroup.rotation.x = walkCycle * 0.55;
          mesh.bodyGroup.position.y = 0.95 + Math.abs(Math.sin(ag.animTime * 20)) * 0.08;
          mesh.headGroup.rotation.x = 0;
          mesh.headGroup.rotation.y = 0;
        } else {
          mesh.position.copy(ag.chairPos);
          ag.state = 'WORKING';
        }
      }

      // CELEBRATE (Victory Pose)
      else if (ag.state === 'CELEBRATE') {
        mesh.bodyGroup.position.y = THREE.MathUtils.lerp(mesh.bodyGroup.position.y, 0.95, 0.1);
        mesh.leftLegGroup.rotation.x = THREE.MathUtils.lerp(mesh.leftLegGroup.rotation.x, 0, 0.1);
        mesh.rightLegGroup.rotation.x = THREE.MathUtils.lerp(mesh.rightLegGroup.rotation.x, 0, 0.1);

        mesh.rightArmGroup.rotation.x = -Math.PI * 0.88;
        mesh.rightArmGroup.rotation.z = -0.2;
        mesh.leftArmGroup.rotation.x = Math.sin(ag.animTime * 5) * 0.25;
        mesh.headGroup.rotation.x = -0.2;

        if (ag.animTime > 3.5) {
          ag.state = 'IDLE_ACTIVITY';
          ag.activityState = null;
        }
      }

      // IDLE ACTIVITIES (Football, Tennis, Gym, Spectator)
      else {
        const slot = ag.activityState || 'IDLE_ROAM';
        const dist = mesh.position.distanceTo(ag.targetPos);

        // 1. Football Striker (Full Dynamic Penalty Sprint & Kick Sequence!)
        if (slot === 'FB_STRIKER') {
          mesh.rotation.y = Math.PI; // Face North towards goal
          const cycle = this.footballState.time % 5.0;

          if (cycle < 1.6) {
            // Stage 1: Running sprint towards the penalty spot (z: -15.5 -> -20.0)
            const runP = cycle / 1.6;
            mesh.position.set(0, 0, THREE.MathUtils.lerp(-15.5, -20.0, runP));
            mesh.bodyGroup.position.y = 0.95 + Math.abs(Math.sin(ag.animTime * 14)) * 0.08;

            const runCycle = Math.sin(ag.animTime * 14);
            mesh.leftLegGroup.rotation.x = runCycle * 0.75;
            mesh.rightLegGroup.rotation.x = -runCycle * 0.75;
            mesh.leftArmGroup.rotation.x = -runCycle * 0.65;
            mesh.rightArmGroup.rotation.x = runCycle * 0.65;
          } else if (cycle < 2.5) {
            // Stage 2: Plant left foot, explosive right leg kick stroke!
            mesh.position.set(0, 0, -20.2);
            mesh.bodyGroup.position.y = 0.95;
            mesh.rightLegGroup.rotation.x = -1.45; // Right leg swing forward
            mesh.leftLegGroup.rotation.x = 0.35;
            mesh.leftArmGroup.rotation.z = 0.85;
            mesh.rightArmGroup.rotation.z = -0.85;
          } else if (cycle < 4.5) {
            // Stage 3: Victory Goal Knee Slide / Fist Pump
            mesh.position.set(0, 0, -20.8);
            mesh.bodyGroup.position.y = 0.95 + Math.sin(ag.animTime * 6) * 0.08;
            mesh.leftLegGroup.rotation.x = 0;
            mesh.rightLegGroup.rotation.x = 0;
            mesh.leftArmGroup.rotation.x = -Math.PI * 0.85;
            mesh.rightArmGroup.rotation.x = -Math.PI * 0.85;
          } else {
            // Stage 4: Jog back to starting mark (-15.5)
            const resetP = (cycle - 4.5) / 0.5;
            mesh.position.set(0, 0, THREE.MathUtils.lerp(-20.8, -15.5, resetP));
          }
        }

        // 2. Football Goalkeeper (Lateral Shuffle & Diving Leap Across Goalmouth)
        else if (slot === 'FB_KEEPER') {
          mesh.rotation.y = 0; // Face South towards striker
          const cycle = this.footballState.time % 5.0;

          if (cycle < 1.6) {
            // Stage 1: Lateral hopping & tracking striker
            const shuffleX = Math.sin(ag.animTime * 5.0) * 1.1;
            mesh.position.set(shuffleX, 0, -30.8);
            mesh.bodyGroup.position.y = 0.88;
            mesh.leftLegGroup.rotation.x = -0.25;
            mesh.rightLegGroup.rotation.x = -0.25;
            mesh.leftArmGroup.rotation.x = -0.6;
            mesh.rightArmGroup.rotation.x = -0.6;
            mesh.rotation.z = 0;
          } else if (cycle < 2.8) {
            // Stage 2: Diving leap across goalmouth to intercept ball!
            const diveP = (cycle - 1.6) / 1.2;
            const diveX = THREE.MathUtils.lerp(0, this.footballState.shotTargetX * 0.9, diveP);
            mesh.position.set(diveX, 0, -30.8);
            mesh.bodyGroup.position.y = 1.35; // Leap in air
            mesh.rotation.z = (this.footballState.shotTargetX > 0 ? 1 : -1) * 0.65; // Tilt body
            mesh.leftArmGroup.rotation.x = -1.5;
            mesh.rightArmGroup.rotation.x = -1.5;
          } else {
            // Stage 3: Landing & getting back to center
            mesh.rotation.z = 0;
            mesh.position.set(0, 0, -30.8);
            mesh.bodyGroup.position.y = 0.88;
          }
        }

        // Standard walking to spot for other activities
        else if (dist > 0.35) {
          const dir = new THREE.Vector3().subVectors(ag.targetPos, mesh.position).normalize();
          mesh.rotation.y = THREE.MathUtils.lerp(mesh.rotation.y, Math.atan2(dir.x, dir.z), 0.12);
          mesh.position.addScaledVector(dir, ag.walkSpeed * 0.9 * delta);

          const walkCycle = Math.sin(ag.animTime * 8.5);
          mesh.leftLegGroup.rotation.x = walkCycle * 0.55;
          mesh.rightLegGroup.rotation.x = -walkCycle * 0.55;
          mesh.leftArmGroup.rotation.x = -walkCycle * 0.45;
          mesh.rightArmGroup.rotation.x = walkCycle * 0.45;
          mesh.bodyGroup.position.y = 0.95 + Math.abs(Math.sin(ag.animTime * 17)) * 0.06;
          mesh.headGroup.rotation.x = 0;
        } else {
          mesh.position.copy(ag.targetPos);

          // 3. Table 1 Ping Pong Players
          if (slot === 'T1_A' || slot === 'T1_B') {
            const isPlayerA = slot === 'T1_A';
            mesh.rotation.y = isPlayerA ? 0 : Math.PI;
            mesh.bodyGroup.position.y = 0.90;
            mesh.leftLegGroup.rotation.x = -0.15;
            mesh.rightLegGroup.rotation.x = -0.15;

            if (p1_ready && p2_ready) {
              const isTurn = isPlayerA ? (this.pingPongCourt1.side === -1 && this.pingPongCourt1.progress > 0.55)
                                       : (this.pingPongCourt1.side === 1 && this.pingPongCourt1.progress > 0.55);

              if (isTurn) {
                const swing = Math.sin(this.pingPongCourt1.progress * Math.PI) * 1.5;
                mesh.rightArmGroup.rotation.x = -Math.PI * 0.35 - swing;
                mesh.rightArmGroup.rotation.y = swing * 0.6;
                mesh.leftArmGroup.rotation.x = 0.2;
              } else {
                mesh.rightArmGroup.rotation.x = -0.6;
                mesh.rightArmGroup.rotation.y = 0;
                mesh.leftArmGroup.rotation.x = -0.4;
              }
            } else {
              mesh.rightArmGroup.rotation.x = -0.4;
              mesh.rightArmGroup.rotation.y = 0;
              mesh.leftArmGroup.rotation.x = -0.2;
            }
          }

          // 4. Spectator Lounge Couch
          else if (slot === 'LOUNGE_QUEUE') {
            mesh.rotation.y = Math.PI / 2;
            mesh.bodyGroup.position.y = 0.68;
            mesh.leftLegGroup.rotation.x = -Math.PI / 2.2;
            mesh.rightLegGroup.rotation.x = -Math.PI / 2.2;

            const clap = Math.sin(ag.animTime * 6) * 0.22;
            mesh.leftArmGroup.rotation.x = -0.7 + clap;
            mesh.rightArmGroup.rotation.x = -0.7 - clap;
            mesh.headGroup.rotation.y = Math.sin(ag.animTime * 2) * 0.25;
          }

          // 5. Gym Treadmill
          else if (slot === 'GYM_TREAD') {
            mesh.rotation.y = Math.PI;
            mesh.bodyGroup.position.y = 1.05 + Math.abs(Math.sin(ag.animTime * 14)) * 0.08;
            const runCycle = Math.sin(ag.animTime * 14);
            mesh.leftLegGroup.rotation.x = runCycle * 0.75;
            mesh.rightLegGroup.rotation.x = -runCycle * 0.75;
            mesh.leftArmGroup.rotation.x = -runCycle * 0.65;
            mesh.rightArmGroup.rotation.x = runCycle * 0.65;
          }

          // 6. Gym Boxing Sparring Pod
          else if (slot === 'GYM_BOXING') {
            mesh.rotation.y = 0;
            mesh.bodyGroup.position.y = 0.95;
            const jabL = Math.sin(ag.animTime * 7) > 0.5 ? -1.3 : -0.5;
            const jabR = Math.cos(ag.animTime * 7) > 0.5 ? -1.3 : -0.5;
            mesh.leftArmGroup.rotation.x = jabL;
            mesh.rightArmGroup.rotation.x = jabR;
            mesh.leftLegGroup.rotation.x = -0.15;
            mesh.rightLegGroup.rotation.x = 0.15;
          }
        }
      }
    });
  }

  updateVisuals(delta) {
    const time = this.clock.getElapsedTime();

    if (this.centralCore) {
      this.centralCore.rotation.x = time * 0.4;
      this.centralCore.rotation.y = time * 0.6;
      this.centralCore.position.y = 1.8 + Math.sin(time * 2) * 0.15;
    }

    Object.values(this.stationObjects).forEach(stObj => {
      if (stObj.monitorTexture && stObj.monitorTexture.updateAnim) {
        stObj.monitorTexture.updateAnim(time);
        stObj.monitorTexture.needsUpdate = true;
      }
    });

    for (let i = this.activeBeams.length - 1; i >= 0; i--) {
      const b = this.activeBeams[i];
      b.progress += delta * b.speed;
      if (b.progress >= 1.0) {
        this.scene.remove(b.mesh);
        this.activeBeams.splice(i, 1);
      } else {
        const pt = b.curve.getPoint(b.progress);
        b.mesh.position.copy(pt);
      }
    }
  }

  setActiveStation(stationId, actionLabel = '', modelName = '') {
    this.activeStation = stationId;

    this.stations.forEach(st => {
      const isTarget = (st.id === stationId);
      st.active = isTarget;

      const obj = this.stationObjects[st.id];
      const agent = this.agents[st.id];

      if (isTarget) {
        if (actionLabel) st.action = actionLabel;
        if (modelName) st.sub = modelName;

        if (agent && agent.state !== 'WORKING') {
          agent.state = 'WALK_TO_DESK';
          agent.animTime = 0;
        }

        if (st.id !== 'pm') {
          this.emitDataPacket('pm', st.id, st.colorHex);
        }

        if (obj && obj.pointLight) obj.pointLight.intensity = this.isLight ? 1.5 : 2.2;
      } else {
        if (st.id !== 'pm' && agent && agent.state === 'WORKING') {
          agent.state = 'CELEBRATE';
          agent.animTime = 0;
        }
        if (obj && obj.pointLight) obj.pointLight.intensity = this.isLight ? 0.4 : 0.6;
      }

      if (obj && obj.badge && obj.badge.redraw) {
        obj.badge.redraw(isTarget ? actionLabel : '');
      }
    });

    if (this.cameraPresets[stationId]) {
      this.focusCamera(stationId);
    }
  }

  updateStationModel(stationId, modelName, actionText = '') {
    const st = this.stations.find(s => s.id === stationId);
    if (st) {
      if (modelName) st.sub = modelName;
      if (actionText) st.action = actionText;
      const obj = this.stationObjects[stationId];
      if (obj && obj.badge && obj.badge.redraw) {
        obj.badge.redraw(actionText);
      }
    }
  }

  updateRoles(rolesList) {
    if (!rolesList || !Array.isArray(rolesList)) return;
    const roleMap = {};
    rolesList.forEach(r => { roleMap[r.id] = r; });

    this.stations.forEach(st => {
      if (st.roleId && roleMap[st.roleId]) {
        const r = roleMap[st.roleId];
        st.sub = r.model_name || r.assigned_model || st.sub;
        const obj = this.stationObjects[st.id];
        if (obj && obj.badge && obj.badge.redraw) {
          obj.badge.redraw(st.action);
        }
      }
    });
  }

  focusCamera(presetKey) {
    const preset = this.cameraPresets[presetKey] || this.cameraPresets.overview;
    this.targetCameraPos.copy(preset.pos);
    this.targetCameraLookAt.copy(preset.target);

    document.querySelectorAll('.btn-cam-view').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-view') === presetKey);
    });
  }

  zoomCamera(deltaDistance) {
    const offset = new THREE.Vector3().subVectors(this.targetCameraPos, this.targetCameraLookAt);
    const curDist = offset.length();
    const newDist = THREE.MathUtils.clamp(curDist + deltaDistance, 3.5, 75.0);
    offset.normalize().multiplyScalar(newDist);
    this.targetCameraPos.copy(this.targetCameraLookAt).add(offset);
  }

  panCamera(deltaX, deltaZ) {
    // Camera right and forward vectors
    const forward = new THREE.Vector3().subVectors(this.targetCameraLookAt, this.targetCameraPos);
    forward.y = 0;
    forward.normalize();
    const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

    const move = new THREE.Vector3()
      .addScaledVector(right, deltaX)
      .addScaledVector(forward, deltaZ);

    this.targetCameraPos.add(move);
    this.targetCameraLookAt.add(move);
  }

  orbitCamera(deltaAngleX, deltaAngleY) {
    const offset = new THREE.Vector3().subVectors(this.targetCameraPos, this.targetCameraLookAt);
    let radius = offset.length();
    let theta = Math.atan2(offset.x, offset.z);
    let phi = Math.acos(THREE.MathUtils.clamp(offset.y / radius, -1, 1));

    theta -= deltaAngleX;
    phi = THREE.MathUtils.clamp(phi - deltaAngleY, 0.15, Math.PI / 2 - 0.05);

    offset.x = radius * Math.sin(phi) * Math.sin(theta);
    offset.y = radius * Math.cos(phi);
    offset.z = radius * Math.sin(phi) * Math.cos(theta);

    this.targetCameraPos.copy(this.targetCameraLookAt).add(offset);
  }

  setupCameraControlsUI() {
    // 1. Preset buttons
    document.querySelectorAll('.btn-cam-view').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const view = e.currentTarget.getAttribute('data-view');
        this.focusCamera(view);
      });
    });

    // 2. On-screen Zoom HUD buttons
    const btnIn = document.getElementById('btn-zoom-in');
    const btnOut = document.getElementById('btn-zoom-out');
    const btnReset = document.getElementById('btn-zoom-reset');

    if (btnIn) btnIn.addEventListener('click', () => this.zoomCamera(-3.5));
    if (btnOut) btnOut.addEventListener('click', () => this.zoomCamera(3.5));
    if (btnReset) btnReset.addEventListener('click', () => this.focusCamera('overview'));

    // 3. Mouse Wheel / Trackpad Pinch Zoom on Canvas
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomDelta = e.deltaY * 0.04;
      this.zoomCamera(zoomDelta);
    }, { passive: false });

    // 4. Mouse Drag to Orbit & Pan Canvas
    let isDragging = false;
    let dragButton = 0; // 0 = Left, 2 = Right
    let prevMouseX = 0;
    let prevMouseY = 0;

    this.canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      dragButton = e.button;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - prevMouseX;
      const dy = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      if (dragButton === 0 && !e.shiftKey) {
        // Left click drag: Orbit around target
        this.orbitCamera(dx * 0.006, dy * 0.006);
      } else {
        // Right click or Shift+Left drag: Pan scene
        this.panCamera(-dx * 0.04, dy * 0.04);
      }
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    // 5. Global Keyboard Zoom & Pan Navigation
    window.addEventListener('keydown', (e) => {
      // Don't trigger when user is typing in chat/input/editor fields
      const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || document.activeElement.isContentEditable) {
        return;
      }

      switch (e.code) {
        case 'Equal': // '+' key
        case 'NumpadAdd':
        case 'KeyW':
        case 'ArrowUp':
        case 'PageUp':
          this.zoomCamera(-2.5);
          break;

        case 'Minus': // '-' key
        case 'NumpadSubtract':
        case 'KeyS':
        case 'ArrowDown':
        case 'PageDown':
          this.zoomCamera(2.5);
          break;

        case 'KeyA':
        case 'ArrowLeft':
          this.panCamera(-1.5, 0);
          break;

        case 'KeyD':
        case 'ArrowRight':
          this.panCamera(1.5, 0);
          break;

        case 'KeyR':
          this.focusCamera('overview');
          break;
      }
    });
  }

  setupInteractions() {
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.scene.children, true);

      if (intersects.length > 0) {
        let hitObj = intersects[0].object;
        while (hitObj && hitObj.parent && hitObj.parent !== this.scene) {
          hitObj = hitObj.parent;
        }

        for (const [stId, obj] of Object.entries(this.stationObjects)) {
          if (hitObj === obj) {
            this.focusCamera(stId);
            this.setActiveStation(stId, 'Фокус на станции');
            break;
          }
        }
      }
    });
  }


  setRecreationVisibility(mode = null, isBusy = false) {
    this.recreationMode = mode || localStorage.getItem('ant_recreation_mode') || 'auto';
    const shouldShow = (this.recreationMode === 'always_show') || (this.recreationMode === 'auto' && !isBusy);

    if (this.pingPongGroup) this.pingPongGroup.visible = shouldShow;
    if (this.gymGroup) this.gymGroup.visible = shouldShow;
    if (this.footballGroup) this.footballGroup.visible = shouldShow;
    if (this.footballBall) this.footballBall.visible = shouldShow;

    // Toggle camera preset buttons in topbar
    const ppBtn = document.querySelector('.btn-cam-view[data-view="pingpong"]');
    const gymBtn = document.querySelector('.btn-cam-view[data-view="gym"]');
    const fbBtn = document.querySelector('.btn-cam-view[data-view="football"]');

    if (ppBtn) ppBtn.style.display = shouldShow ? '' : 'none';
    if (gymBtn) gymBtn.style.display = shouldShow ? '' : 'none';
    if (fbBtn) fbBtn.style.display = shouldShow ? '' : 'none';

    // If recreation is hidden, redirect all idle agents to roam near workstations
    if (!shouldShow && this.agents) {
      Object.values(this.agents).forEach(ag => {
        if (ag.state !== 'WORKING' && ag.state !== 'WALK_TO_DESK') {
          ag.activityState = 'IDLE_ROAM';
          ag.activityLabel = 'В офисе (Ожидание)';
        }
      });
    }
  }

  getShortRoleName(name) {
    if (!name) return 'Агент';
    if (name.includes('разработчик')) return 'Разработчик';
    if (name.includes('QA') || name.includes('тестирования')) return 'QA Инженер';
    if (name.includes('безопасности')) return 'Безопасность';
    if (name.includes('Дизайн') || name.includes('UI/UX')) return 'Дизайнер';
    if (name.includes('Аналитик')) return 'Аналитик';
    if (name.includes('DevOps')) return 'DevOps';
    if (name.includes('PM') || name.includes('управление')) return 'PM';
    return name.split(' ')[0];
  }

  saveSwarmState() {
    try {
      const state = {
        agents: {},
        football: { pos: new THREE.Vector3(0, 9.5, -11.0), target: new THREE.Vector3(0, 0.8, -23.5) },
        pingPong: {
          scoreA: this.pingPongCourt1 ? this.pingPongCourt1.scoreA : 5,
          scoreB: this.pingPongCourt1 ? this.pingPongCourt1.scoreB : 4,
          playerAName: this.pingPongCourt1 ? this.pingPongCourt1.playerAName : 'Разработчик',
          playerBName: this.pingPongCourt1 ? this.pingPongCourt1.playerBName : 'QA Инженер'
        }
      };
      if (this.agents) {
        Object.entries(this.agents).forEach(([id, ag]) => {
          state.agents[id] = {
            state: ag.state,
            activityState: ag.activityState,
            pos: { x: ag.mesh.position.x, y: ag.mesh.position.y, z: ag.mesh.position.z },
            rotY: ag.mesh.rotation.y
          };
        });
      }
      localStorage.setItem('ant_hive_swarm_state', JSON.stringify(state));
    } catch (e) {}
  }

  restoreSwarmState() {
    try {
      const raw = localStorage.getItem('ant_hive_swarm_state');
      if (!raw) return;
      const state = JSON.parse(raw);
      if (state.football && this.footballState) {
        this.footballState.scoreStriker = (state.football.scoreStriker > 5) ? 0 : (state.football.scoreStriker || 0);
        this.footballState.scoreKeeper = (state.football.scoreKeeper > 5) ? 0 : (state.football.scoreKeeper || 0);
        if (state.football.strikerName) this.footballState.strikerName = state.football.strikerName;
        if (state.football.keeperName) this.footballState.keeperName = state.football.keeperName;
        this.redrawFootballScoreboard();
      }
      if (state.pingPong && this.pingPongCourt1) {
        this.pingPongCourt1.scoreA = state.pingPong.scoreA || 0;
        this.pingPongCourt1.scoreB = state.pingPong.scoreB || 0;
        if (state.pingPong.playerAName) this.pingPongCourt1.playerAName = state.pingPong.playerAName;
        if (state.pingPong.playerBName) this.pingPongCourt1.playerBName = state.pingPong.playerBName;
        this.redrawPingPongScoreboard();
      }
      if (state.agents && this.agents) {
        Object.entries(state.agents).forEach(([id, saved]) => {
          const ag = this.agents[id];
          if (ag && saved) {
            ag.state = saved.state || ag.state;
            ag.activityState = saved.activityState || ag.activityState;
            if (saved.pos) {
              ag.mesh.position.set(saved.pos.x, saved.pos.y, saved.pos.z);
              ag.targetPos.set(saved.pos.x, saved.pos.y, saved.pos.z);
            }
            if (saved.rotY !== undefined) ag.mesh.rotation.y = saved.rotY;
          }
        });
      }
    } catch (e) {}
  }

  onResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const w = this.container.clientWidth || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  setTheme(isLight) {
    this.isLight = isLight;
    if (!this.scene) return;

    const bgCol = isLight ? 0xf8fafc : 0x070b14;
    this.scene.background = new THREE.Color(bgCol);
    if (this.scene.fog) {
      this.scene.fog.color = new THREE.Color(bgCol);
      this.scene.fog.density = isLight ? 0.012 : 0.022;
    }

    if (this.renderer) {
      this.renderer.toneMappingExposure = isLight ? 1.35 : 1.15;
    }

    // Floor
    if (this.floorMat) {
      this.floorMat.color.setHex(isLight ? 0xf1f5f9 : 0x0c1322);
      this.floorMat.metalness = isLight ? 0.15 : 0.75;
      this.floorMat.roughness = isLight ? 0.35 : 0.25;
    }

    // Grid helper
    if (this.gridHelper) {
      this.scene.remove(this.gridHelper);
      this.gridHelper = new THREE.GridHelper(70, 35, isLight ? 0x6366f1 : 0x3b82f6, isLight ? 0xd1d5db : 0x1e293b);
      this.gridHelper.position.y = 0.01;
      this.scene.add(this.gridHelper);
    }

    // PM Platform
    if (this.pmPlatMat) {
      this.pmPlatMat.color.setHex(isLight ? 0xffffff : 0x181e36);
      this.pmPlatMat.metalness = isLight ? 0.2 : 0.85;
    }

    // High Key Studio Lighting in Light Mode
    if (this.ambientLight) {
      this.ambientLight.intensity = isLight ? 1.4 : 0.7;
    }
    if (this.dirLight) {
      this.dirLight.color.setHex(isLight ? 0xffffff : 0xdbeafe);
      this.dirLight.intensity = isLight ? 1.8 : 1.2;
    }
    if (this.bluePoint) {
      this.bluePoint.intensity = isLight ? 1.2 : 2.0;
    }

    // Update workstation materials (pedestals, desks, chairs, badges)
    Object.values(this.stationObjects).forEach(group => {
      if (group.pedestalMat) {
        group.pedestalMat.color.setHex(isLight ? 0xffffff : 0x11192e);
        group.pedestalMat.metalness = isLight ? 0.2 : 0.8;
      }
      if (group.deskMat) {
        group.deskMat.color.setHex(isLight ? 0xffffff : 0x1e293b);
        group.deskMat.metalness = isLight ? 0.1 : 0.8;
      }
      if (group.chairMat) {
        group.chairMat.color.setHex(isLight ? 0xe2e8f0 : 0x0f172a);
      }
      if (group.badge && group.badge.redraw) {
        group.badge.redraw(group.stationData ? group.stationData.action : '');
      }
    });

    // Update Agent armor & joint colors for clean Light & Dark aesthetics
    Object.values(this.agents).forEach(ag => {
      if (ag.mesh && ag.mesh.armorMat) {
        ag.mesh.armorMat.color.setHex(isLight ? 0x1e293b : 0xf8fafc);
        ag.mesh.armorMat.metalness = isLight ? 0.6 : 0.35;
        ag.mesh.armorMat.roughness = isLight ? 0.3 : 0.18;
      }
      if (ag.mesh && ag.mesh.jointMat) {
        ag.mesh.jointMat.color.setHex(isLight ? 0x64748b : 0x334155);
      }
    });
    if (this.redrawPingPongScoreboard) {
      this.redrawPingPongScoreboard();
    }
  }

  // Har 1.5 soniyada FPS ni o'lchab, sifat rejimini avtomatik sozlaydi.
  _sampleQualityFps(nowMs) {
    const q = this.quality;
    q.framesInWindow++;
    const elapsed = nowMs - q.lastCheck;
    if (elapsed < q.windowMs) return;

    const fps = (q.framesInWindow / elapsed) * 1000;
    q.fpsHistory.push(fps);
    if (q.fpsHistory.length > 10) q.fpsHistory.shift();
    q.framesInWindow = 0;
    q.lastCheck = nowMs;

    if (q.manuallySet) return;

    // Median FPS — bir vaqtincha zarba bilan sifat sakramasin.
    const sorted = [...q.fpsHistory].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)] || fps;

    let newMode = q.mode;
    if (median < 28 && q.mode !== 'low') newMode = 'low';
    else if (median >= 30 && median < 50 && q.mode !== 'medium') newMode = 'medium';
    else if (median >= 55 && q.mode !== 'high') newMode = 'high';

    if (newMode !== q.mode) this._applyQualityMode(newMode);
  }

  _applyQualityMode(mode) {
    const q = this.quality;
    q.mode = mode;
    if (mode === 'high') {
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = true;
      q.farSkipFrames = 1;
    } else if (mode === 'medium') {
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
      this.renderer.shadowMap.enabled = true;
      q.farSkipFrames = 2;
    } else {
      // low
      this.renderer.setPixelRatio(1.0);
      this.renderer.shadowMap.enabled = false;
      q.farSkipFrames = 3;
    }
    // Ba'zi materiallarning shadow xususiyati o'zgargani bilan qayta compile talab qilishi mumkin.
    if (this.scene) {
      this.scene.traverse(obj => {
        if (obj.material && obj.material.needsUpdate !== undefined) {
          obj.material.needsUpdate = true;
        }
      });
    }
  }

  // Foydalanuvchi qo'lda sifatni belgilashi mumkin bo'lgan public API.
  setQualityMode(mode) {
    if (!['high', 'medium', 'low', 'auto'].includes(mode)) return;
    if (mode === 'auto') {
      this.quality.manuallySet = false;
      return;
    }
    this.quality.manuallySet = true;
    this._applyQualityMode(mode);
  }

  getPerformanceStats() {
    const q = this.quality;
    const avgFps = q.fpsHistory.length
      ? q.fpsHistory.reduce((a, b) => a + b, 0) / q.fpsHistory.length
      : 0;
    return {
      mode: q.mode,
      fps: Math.round(avgFps),
      pixelRatio: this.renderer.getPixelRatio(),
      shadows: this.renderer.shadowMap.enabled,
      farSkipFrames: q.farSkipFrames,
    };
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    const delta = this.clock.getDelta();
    const nowMs = performance.now();
    this._sampleQualityFps(nowMs);
    this.quality.frameIndex++;

    if (this.controls) {
      this.camera.position.lerp(this.targetCameraPos, 0.05);
      this.controls.target.lerp(this.targetCameraLookAt, 0.05);
      this.controls.update();
    }

    this.updateAgents(delta);
    this.updateVisuals(delta);

    this.renderer.render(this.scene, this.camera);
  }

  // =============================================================
  // Dynamic 3D Speech Bubbles & Idle Robot Chatter Engine
  // =============================================================
  showSpeechBubble(agentId, text, colorHex = 0x8b5cf6, duration = 4500) {
    const ag = this.agents[agentId];
    if (!ag || !ag.mesh) return;

    if (ag.speechSprite) {
      ag.mesh.remove(ag.speechSprite);
      ag.speechSprite = null;
    }

    const cvs = document.createElement('canvas');
    cvs.width = 400;
    cvs.height = 140;
    const ctx = cvs.getContext('2d');

    const isLight = this.isLight;
    ctx.clearRect(0, 0, 400, 140);

    // Rounded Bubble with Pointer
    ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(15, 23, 42, 0.94)';
    ctx.strokeStyle = typeof colorHex === 'string' ? colorHex : ('#' + colorHex.toString(16).padStart(6, '0'));
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(8, 8, 384, 96, 16);
    ctx.fill();
    ctx.stroke();

    // Bubble pointer down
    ctx.fillStyle = isLight ? 'rgba(255, 255, 255, 0.96)' : 'rgba(15, 23, 42, 0.94)';
    ctx.beginPath();
    ctx.moveTo(185, 104);
    ctx.lineTo(200, 128);
    ctx.lineTo(215, 104);
    ctx.fill();
    ctx.stroke();

    // Speaker Name Tag
    const st = this.stations.find(s => s.id === agentId);
    const roleName = st ? st.name.split(' ')[0] : agentId.toUpperCase();
    ctx.fillStyle = ctx.strokeStyle;
    ctx.font = 'bold 16px Plus Jakarta Sans, sans-serif';
    ctx.fillText(`[ ${roleName} ]`, 24, 34);

    // Dialog Text
    ctx.fillStyle = isLight ? '#0f172a' : '#f8fafc';
    ctx.font = '600 15px Plus Jakarta Sans, sans-serif';
    
    // Simple wrap text
    const words = text.split(' ');
    let line1 = '', line2 = '';
    words.forEach(w => {
      if ((line1 + w).length < 32 && !line2) line1 += w + ' ';
      else line2 += w + ' ';
    });

    ctx.fillText(line1.trim(), 24, 62);
    if (line2) ctx.fillText(line2.trim(), 24, 86);

    const tex = new THREE.CanvasTexture(cvs);
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
    const sprite = new THREE.Sprite(mat);
    sprite.position.set(0, 2.7, 0);
    sprite.scale.set(3.8, 1.33, 1);

    ag.mesh.add(sprite);
    ag.speechSprite = sprite;

    setTimeout(() => {
      if (ag.speechSprite === sprite) {
        ag.mesh.remove(sprite);
        ag.speechSprite = null;
      }
    }, duration);
  }

  startIdleDialogueLoop() {
    setInterval(async () => {
      // Trigger dialogue only when idle and window is active
      const idleList = Object.keys(this.agents).filter(id => {
        const ag = this.agents[id];
        return ag && ag.state !== 'WORKING' && ag.state !== 'WALK_TO_DESK';
      });

      if (idleList.length < 2) return;

      try {
        const res = await fetch('/api/hive/dialogue');
        if (!res.ok) return;
        const data = await res.json();

        const spA = idleList.includes(data.speaker_a) ? data.speaker_a : idleList[0];
        const spB = idleList.includes(data.speaker_b) ? data.speaker_b : idleList[1];

        const agA = this.agents[spA];
        const agB = this.agents[spB];
        if (agA && agB) {
          // Face each other
          const dir = new THREE.Vector3().subVectors(agB.mesh.position, agA.mesh.position).normalize();
          agA.mesh.rotation.y = Math.atan2(dir.x, dir.z);
          agB.mesh.rotation.y = Math.atan2(-dir.x, -dir.z);

          // Head nod gesture
          agA.animTime += 1.5;
          agB.animTime += 2.0;

          // First speaker
          this.showSpeechBubble(spA, data.text_a, 0x8b5cf6, 4200);

          // Second speaker response
          setTimeout(() => {
            this.showSpeechBubble(spB, data.text_b, 0x06b6d4, 4500);
          }, 3200);
        }
      } catch (e) {
        // Silent
      }
    }, 14000);
  }

}

window.IsometricHive3D = IsometricHive3D;



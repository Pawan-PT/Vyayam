/* vyayam3d.js — Procedural 3D Figure for VYAYAM
 * Builds a humanoid figure from THREE.js primitives (no GLB required).
 * Drives pose from joint-angle data passed via setPose().
 * API: window.Vyayam3D = { init, setPose, setError, destroy }
 * Requires Three.js r128 loaded externally.
 */
(function () {
  'use strict';

  var _renderer, _scene, _camera, _animId;
  var _initialized = false;
  var _pendingPose = null;

  // Lerp state
  var _prevJoints = {};
  var _currentJoints = {};
  var _lerpT = 1.0;
  var _lerpDuration = 1500;
  var _lerpStart = 0;

  // Figure joint groups
  var _fig = {};
  var _bodyMat, _jointMat, _errorMat;
  var _errorGroups = {};
  var _pulseTick = 0;

  var PI = Math.PI;
  var DEG = PI / 180;

  // ── Build the procedural humanoid figure ────────────────────────────────────
  function buildFigure(scene) {
    var bodyColor  = 0x38bdf8;
    var jointColor = 0x93c5fd;

    _bodyMat  = new THREE.MeshStandardMaterial({ color: bodyColor,  roughness: 0.4, metalness: 0.3, emissive: bodyColor,  emissiveIntensity: 0.12 });
    _jointMat = new THREE.MeshStandardMaterial({ color: jointColor, roughness: 0.3, metalness: 0.5, emissive: jointColor, emissiveIntensity: 0.18 });
    _errorMat = new THREE.MeshStandardMaterial({ color: 0xff3232,   roughness: 0.3, metalness: 0.3, emissive: 0xff3232,   emissiveIntensity: 0.5  });

    // Proportions (meters; total height ≈ 1.70m)
    var P = {
      pelvisH:   0.12,
      spineH:    0.17,
      neckH:     0.09,
      headR:     0.10,
      shoulderW: 0.18,
      hipW:      0.085,
      upperArmL: 0.27,
      foreArmL:  0.24,
      handR:     0.040,
      upperLegL: 0.40,
      shinL:     0.36,
      footR:     0.06,
      limR:      0.036,  // limb radius
      jntR:      0.045,  // joint sphere radius
    };

    function cyl(len, r, mat) {
      var g = new THREE.CylinderGeometry(r * 0.75, r, len, 10);
      g.translate(0, len / 2, 0);  // pivot at base
      return new THREE.Mesh(g, mat);
    }
    function ball(r, mat) {
      return new THREE.Mesh(new THREE.SphereGeometry(r, 10, 8), mat);
    }
    function grp(name) {
      var g = new THREE.Group(); g.name = name; return g;
    }

    // Root group — sits at hip height so feet land near y=0
    var root = grp('hips');
    root.position.set(0, 0.87, 0);
    scene.add(root);
    _fig.hips = root;

    // ── Pelvis block (visual only) ────────────────────────
    var pelvisMesh = cyl(P.pelvisH, P.limR * 1.4, _bodyMat);
    pelvisMesh.rotation.x = PI;          // point downward
    root.add(pelvisMesh);
    root.add(ball(P.jntR * 1.1, _jointMat));

    // ── Spine chain (goes UP from hips) ──────────────────
    var spine = grp('spine');
    spine.position.set(0, P.pelvisH * 0.5, 0);
    root.add(spine); _fig.spine = spine;
    spine.add(cyl(P.spineH, P.limR * 1.1, _bodyMat));

    var spine1 = grp('spine1');
    spine1.position.set(0, P.spineH, 0);
    spine.add(spine1); _fig.spine1 = spine1;
    spine1.add(ball(P.jntR * 0.85, _jointMat));
    spine1.add(cyl(P.spineH, P.limR * 1.0, _bodyMat));

    var spine2 = grp('spine2');
    spine2.position.set(0, P.spineH, 0);
    spine1.add(spine2); _fig.spine2 = spine2;
    spine2.add(ball(P.jntR * 0.80, _jointMat));
    spine2.add(cyl(P.spineH * 0.75, P.limR * 0.9, _bodyMat));

    // Cross-bar (shoulder line visual)
    var crossGeo = new THREE.CylinderGeometry(P.limR * 0.7, P.limR * 0.7, P.shoulderW * 2, 8);
    crossGeo.rotateZ(PI / 2);
    spine2.add(new THREE.Mesh(crossGeo, _bodyMat));

    var neck = grp('neck');
    neck.position.set(0, P.spineH * 0.75, 0);
    spine2.add(neck); _fig.neck = neck;
    neck.add(cyl(P.neckH, P.limR * 0.65, _bodyMat));

    var headGrp = grp('head');
    headGrp.position.set(0, P.neckH, 0);
    neck.add(headGrp); _fig.head = headGrp;
    headGrp.add(ball(P.headR, _bodyMat));

    // ── Shoulder offsets (children of spine2) ─────────────
    var lSho = grp('lShoulder');
    lSho.position.set(-P.shoulderW, P.spineH * 0.65, 0);
    spine2.add(lSho); _fig.lShoulder = lSho;
    lSho.add(ball(P.jntR * 0.9, _jointMat));

    var rSho = grp('rShoulder');
    rSho.position.set(P.shoulderW, P.spineH * 0.65, 0);
    spine2.add(rSho); _fig.rShoulder = rSho;
    rSho.add(ball(P.jntR * 0.9, _jointMat));

    // ── Arms: hang DOWN in rest pose ──────────────────────
    // Cylinder pivots at top, extends downward.
    // rotation.x tilts arm forward/back; rotation.z tilts arm left/right.

    var lArm = grp('lArm');
    lSho.add(lArm); _fig.lArm = lArm;
    var lArmMesh = cyl(P.upperArmL, P.limR, _bodyMat);
    lArmMesh.rotation.x = PI;  // point downward
    lArm.add(lArmMesh);

    var lFA = grp('lForeArm');
    lFA.position.set(0, -P.upperArmL, 0);
    lArm.add(lFA); _fig.lForeArm = lFA;
    lFA.add(ball(P.jntR * 0.8, _jointMat));
    var lFAMesh = cyl(P.foreArmL, P.limR * 0.82, _bodyMat);
    lFAMesh.rotation.x = PI;
    lFA.add(lFAMesh);

    var lHand = grp('lHand');
    lHand.position.set(0, -P.foreArmL, 0);
    lFA.add(lHand); _fig.lHand = lHand;
    lHand.add(ball(P.handR, _bodyMat));

    var rArm = grp('rArm');
    rSho.add(rArm); _fig.rArm = rArm;
    var rArmMesh = cyl(P.upperArmL, P.limR, _bodyMat);
    rArmMesh.rotation.x = PI;
    rArm.add(rArmMesh);

    var rFA = grp('rForeArm');
    rFA.position.set(0, -P.upperArmL, 0);
    rArm.add(rFA); _fig.rForeArm = rFA;
    rFA.add(ball(P.jntR * 0.8, _jointMat));
    var rFAMesh = cyl(P.foreArmL, P.limR * 0.82, _bodyMat);
    rFAMesh.rotation.x = PI;
    rFA.add(rFAMesh);

    var rHand = grp('rHand');
    rHand.position.set(0, -P.foreArmL, 0);
    rFA.add(rHand); _fig.rHand = rHand;
    rHand.add(ball(P.handR, _bodyMat));

    // ── Legs: hang DOWN from hips ──────────────────────────
    var lUL = grp('lUpLeg');
    lUL.position.set(-P.hipW, 0, 0);
    root.add(lUL); _fig.lUpLeg = lUL;
    lUL.add(ball(P.jntR * 1.1, _jointMat));
    var lULMesh = cyl(P.upperLegL, P.limR * 1.2, _bodyMat);
    lULMesh.rotation.x = PI;
    lUL.add(lULMesh);

    var lLL = grp('lLeg');
    lLL.position.set(0, -P.upperLegL, 0);
    lUL.add(lLL); _fig.lLeg = lLL;
    lLL.add(ball(P.jntR, _jointMat));
    var lLLMesh = cyl(P.shinL, P.limR, _bodyMat);
    lLLMesh.rotation.x = PI;
    lLL.add(lLLMesh);

    var lFt = grp('lFoot');
    lFt.position.set(0, -P.shinL, 0);
    lLL.add(lFt); _fig.lFoot = lFt;
    lFt.add(ball(P.footR, _jointMat));

    var rUL = grp('rUpLeg');
    rUL.position.set(P.hipW, 0, 0);
    root.add(rUL); _fig.rUpLeg = rUL;
    rUL.add(ball(P.jntR * 1.1, _jointMat));
    var rULMesh = cyl(P.upperLegL, P.limR * 1.2, _bodyMat);
    rULMesh.rotation.x = PI;
    rUL.add(rULMesh);

    var rLL = grp('rLeg');
    rLL.position.set(0, -P.upperLegL, 0);
    rUL.add(rLL); _fig.rLeg = rLL;
    rLL.add(ball(P.jntR, _jointMat));
    var rLLMesh = cyl(P.shinL, P.limR, _bodyMat);
    rLLMesh.rotation.x = PI;
    rLL.add(rLLMesh);

    var rFt = grp('rFoot');
    rFt.position.set(0, -P.shinL, 0);
    rLL.add(rFt); _fig.rFoot = rFt;
    rFt.add(ball(P.footR, _jointMat));
  }

  // ── Reset all bone groups to identity rotation ──────────────────────────────
  function resetFigure() {
    Object.keys(_fig).forEach(function (name) {
      if (_fig[name]) _fig[name].rotation.set(0, 0, 0);
    });
    // Reset root to default upright position and camera
    if (_fig.hips) {
      _fig.hips.position.set(0, 0.87, 0);
      _fig.hips.rotation.set(0, 0, 0);
    }
  }

  // ── Set camera for exercise orientation ─────────────────────────────────────
  function setCameraForPose(joints) {
    if (!_camera) return;
    var k = joints || {};
    var isProne  = k.bodyLine !== undefined;
    var isHang   = (k.elbow !== undefined && k.bodyLine === undefined && k.knee === undefined && k.workingKnee === undefined);
    var isLateral = k.lateralLine !== undefined;

    if (isProne) {
      _camera.position.set(3.2, 0.7, 0.3);
      _camera.lookAt(0, 0.5, 0);
    } else if (isLateral) {
      _camera.position.set(2.8, 0.6, 0.8);
      _camera.lookAt(0, 0.5, 0);
    } else if (isHang) {
      _camera.position.set(0, 1.5, 3.8);
      _camera.lookAt(0, 1.3, 0);
    } else {
      _camera.position.set(0, 1.0, 3.2);
      _camera.lookAt(0, 0.92, 0);
    }
  }

  // ── Apply joint-angle data to the procedural figure ─────────────────────────
  function applyPose(joints) {
    if (!_fig.hips) return;
    var k = joints || {};

    resetFigure();
    setCameraForPose(k);

    // BILATERAL SQUAT / SINGLE-LEG SQUAT
    if (k.knee !== undefined || k.workingKnee !== undefined) {
      var knee  = k.knee  !== undefined ? k.knee  : k.workingKnee;
      var hip   = k.hip   !== undefined ? k.hip   : knee;
      var trunk = k.trunk !== undefined ? k.trunk : 175;

      var kFlex  = Math.max(0, (175 - knee))  * DEG;
      var hFlex  = Math.max(0, (175 - hip))   * DEG;
      var tLean  = Math.max(0, (175 - trunk)) * DEG * 0.45;

      _fig.lUpLeg.rotation.x = -hFlex * 0.88;
      _fig.rUpLeg.rotation.x = -hFlex * 0.88;
      _fig.lUpLeg.rotation.z =  0.10;
      _fig.rUpLeg.rotation.z = -0.10;
      _fig.lLeg.rotation.x   =  kFlex;
      _fig.rLeg.rotation.x   =  kFlex;
      _fig.spine.rotation.x  = -tLean;
      _fig.spine1.rotation.x = -tLean * 0.5;

      if (k.workingKnee !== undefined) {
        // Single-leg: non-working leg rises in front
        _fig.rUpLeg.rotation.x = -0.45;
        _fig.rLeg.rotation.x   = -0.25;
        _fig.rFoot.rotation.x  = 0.0;
        // Arms out for balance
        _fig.lArm.rotation.x = -0.45;
        _fig.rArm.rotation.x = -0.45;
        _fig.lArm.rotation.z = -0.35;
        _fig.rArm.rotation.z =  0.35;
      }
    }

    // HIP HINGE (bilateral or single)
    if ((k.hip !== undefined || k.workingHip !== undefined) &&
        k.knee === undefined && k.workingKnee === undefined && k.bodyLine === undefined) {
      var ha    = k.workingHip !== undefined ? k.workingHip : k.hip;
      var hinge = Math.max(0, (175 - ha)) * DEG;

      _fig.spine.rotation.x  = -hinge * 0.42;
      _fig.spine1.rotation.x = -hinge * 0.28;
      _fig.spine2.rotation.x = -hinge * 0.14;
      _fig.lUpLeg.rotation.x = -hinge * 0.22;
      _fig.rUpLeg.rotation.x = -hinge * 0.22;

      if (k.workingHip !== undefined) {
        // Single-leg hinge: free leg extends back
        _fig.rUpLeg.rotation.x =  hinge * 0.72;
        _fig.rLeg.rotation.x   =  hinge * 0.18;
      }
    }

    // PUSH-UP (elbow + bodyLine)
    if (k.elbow !== undefined && k.bodyLine !== undefined) {
      var eFlex = Math.max(0, (175 - k.elbow)) * DEG;

      // Prone: tip entire figure forward 90°
      _fig.hips.rotation.x = -PI / 2;
      _fig.hips.position.set(0, 0.60, 0.25);

      // Arms: reach forward (down in prone = world -Y = local -Z for prone figure)
      _fig.lArm.rotation.x = -PI / 2;
      _fig.rArm.rotation.x = -PI / 2;
      _fig.lArm.rotation.z = -0.28;
      _fig.rArm.rotation.z =  0.28;

      // Elbow bend
      _fig.lForeArm.rotation.x = -eFlex * 0.9;
      _fig.rForeArm.rotation.x = -eFlex * 0.9;
    }

    // PLANK (bodyLine only — no elbow)
    if (k.bodyLine !== undefined && k.elbow === undefined) {
      var sag = (180 - k.bodyLine) * DEG;

      _fig.hips.rotation.x = -PI / 2;
      _fig.hips.position.set(0, 0.58, 0.20);

      // Forearm plank: arms fold at elbow
      _fig.lArm.rotation.x = -PI / 2;
      _fig.rArm.rotation.x = -PI / 2;
      _fig.lForeArm.rotation.x = -PI / 2;
      _fig.rForeArm.rotation.x = -PI / 2;
      _fig.lArm.rotation.z = -0.24;
      _fig.rArm.rotation.z =  0.24;

      // Hip sag / pike
      _fig.spine.rotation.x = -sag * 0.5;
    }

    // HANG / PULL-UP (elbow only — no bodyLine, no knee)
    if (k.elbow !== undefined && k.bodyLine === undefined &&
        k.knee === undefined && k.workingKnee === undefined) {
      var pullFlex = Math.max(0, (175 - k.elbow)) * DEG;

      // Arms go overhead
      _fig.lArm.rotation.x = -(PI - 0.08);
      _fig.rArm.rotation.x = -(PI - 0.08);
      _fig.lArm.rotation.z = -0.18;
      _fig.rArm.rotation.z =  0.18;

      // Elbow pulls forearm toward body
      _fig.lForeArm.rotation.x =  pullFlex * 0.88;
      _fig.rForeArm.rotation.x =  pullFlex * 0.88;

      // Slight core tuck
      _fig.spine.rotation.x  = -0.05;
      _fig.spine1.rotation.x = -0.05;
    }

    // ARM SPREAD (band pull-apart etc.)
    if (k.armSpread !== undefined) {
      var sp = Math.max(0, k.armSpread - 1.0) * 1.15;
      _fig.lArm.rotation.z = -sp * 0.65;
      _fig.rArm.rotation.z =  sp * 0.65;
      _fig.lArm.rotation.x = -0.22;
      _fig.rArm.rotation.x = -0.22;
      _fig.lForeArm.rotation.z = -sp * 0.25;
      _fig.rForeArm.rotation.z =  sp * 0.25;
    }

    // ROTATION (Russian twist, pallof press etc.)
    if (k.rotation !== undefined) {
      var rot = k.rotation * 8;
      _fig.spine2.rotation.y = rot;
      _fig.spine1.rotation.y = rot * 0.5;
    }

    // LUNGE (knee + trunk, no bilateral hip)
    if (k.knee !== undefined && k.trunk !== undefined && k.hip === undefined) {
      var lk = Math.max(0, (175 - k.knee)) * DEG;
      var lt = Math.max(0, (175 - k.trunk)) * DEG * 0.3;

      _fig.lUpLeg.rotation.x = -lk * 0.68;
      _fig.lLeg.rotation.x   =  lk;
      _fig.rUpLeg.rotation.x =  lk * 0.50;
      _fig.rLeg.rotation.x   =  lk * 0.38;
      _fig.lUpLeg.rotation.z =  0.05;
      _fig.rUpLeg.rotation.z = -0.05;
      _fig.spine.rotation.x  = -lt;
    }

    // BALANCE (hipLevel)
    if (k.hipLevel !== undefined) {
      _fig.rUpLeg.rotation.x = -0.60;
      _fig.rLeg.rotation.x   =  0.38;
      _fig.lArm.rotation.z   = -0.48;
      _fig.rArm.rotation.z   =  0.48;
      _fig.lArm.rotation.x   = -0.22;
      _fig.rArm.rotation.x   = -0.22;
    }

    // LATERAL / SIDE PLANK
    if (k.lateralLine !== undefined) {
      var lat = (180 - k.lateralLine) * DEG;

      _fig.hips.rotation.z = -PI / 2;
      _fig.hips.position.set(0, 0.55, 0);

      // Support arm reaches down
      _fig.rArm.rotation.x = PI / 2;
      _fig.rArm.rotation.z = -0.2;
      // Top arm along body
      _fig.lArm.rotation.z = -1.2;
      // Hip sag
      _fig.spine.rotation.z = -lat * 0.5;
    }

    // SHOULDER (overhead press, stretch)
    if (k.shoulder !== undefined) {
      var shAngle = Math.max(0, k.shoulder - 30) * DEG;
      _fig.lArm.rotation.x = -shAngle * 0.85;
      _fig.rArm.rotation.x = -shAngle * 0.85;
    }
  }

  // ── Lerp between two joint-angle maps ───────────────────────────────────────
  function lerpJoints(a, b, t) {
    var result = {};
    var keys = {};
    Object.keys(a).forEach(function (k) { keys[k] = true; });
    Object.keys(b).forEach(function (k) { keys[k] = true; });
    Object.keys(keys).forEach(function (key) {
      var va = a[key] !== undefined ? a[key] : b[key];
      var vb = b[key] !== undefined ? b[key] : a[key];
      result[key] = va + (vb - va) * t;
    });
    return result;
  }

  // ── Error / highlight bones ──────────────────────────────────────────────────
  var JOINT_TO_SEGS = {
    knee:        ['lLeg', 'rLeg', 'lUpLeg', 'rUpLeg'],
    hip:         ['lUpLeg', 'rUpLeg'],
    trunk:       ['spine', 'spine1'],
    elbow:       ['lForeArm', 'rForeArm'],
    bodyLine:    ['spine', 'spine1'],
    armSpread:   ['lArm', 'rArm'],
    workingKnee: ['lLeg', 'rLeg'],
    workingHip:  ['lUpLeg', 'rUpLeg'],
    lateralLine: ['spine', 'lUpLeg'],
    rotation:    ['spine1', 'spine2'],
    shoulder:    ['lArm', 'rArm'],
    hipLevel:    ['lUpLeg', 'rUpLeg'],
  };

  function setMaterialOnGroup(groupName, mat) {
    var g = _fig[groupName];
    if (!g) return;
    g.traverse(function (obj) {
      if (obj.isMesh) obj.material = mat;
    });
  }

  function resetAllMaterials() {
    Object.keys(_fig).forEach(function (name) {
      var g = _fig[name];
      if (!g) return;
      g.traverse(function (obj) {
        if (!obj.isMesh) return;
        // Restore by material type hint stored in name
        var parent = obj.parent;
        if (parent && (parent.name === 'lShoulder' || parent.name === 'rShoulder' ||
                       parent.name === 'lLeg'      || parent.name === 'rLeg'      ||
                       parent.name === 'lFoot'     || parent.name === 'rFoot'     ||
                       parent.name === 'head'      || parent.name === 'lHand'     ||
                       parent.name === 'rHand')) {
          obj.material = (obj.geometry instanceof THREE.SphereGeometry || obj.geometry.type === 'SphereGeometry') ? _jointMat : _bodyMat;
        } else {
          // Check geometry type
          if (obj.geometry && obj.geometry.parameters && obj.geometry.parameters.thetaLength !== undefined) {
            obj.material = _jointMat;  // sphere
          } else {
            obj.material = _bodyMat;
          }
        }
      });
    });
    // Simpler: just restore all meshes to their default materials
    Object.keys(_fig).forEach(function (name) {
      var g = _fig[name];
      if (!g) return;
      g.traverse(function (obj) {
        if (!obj.isMesh) return;
        // Spheres = joint material, Cylinders = body material
        var isJoint = obj.geometry.type === 'SphereGeometry';
        obj.material = isJoint ? _jointMat : _bodyMat;
      });
    });
    _errorGroups = {};
  }

  // ── Render loop ──────────────────────────────────────────────────────────────
  function renderLoop() {
    _animId = requestAnimationFrame(renderLoop);

    if (_lerpT < 1.0) {
      var elapsed = Date.now() - _lerpStart;
      _lerpT = Math.min(1.0, elapsed / Math.max(_lerpDuration, 100));
      var ease = _lerpT < 0.5
        ? 4 * _lerpT * _lerpT * _lerpT
        : 1 - Math.pow(-2 * _lerpT + 2, 3) / 2;
      applyPose(lerpJoints(_prevJoints, _currentJoints, ease));
    }

    // Pulse error emissive
    if (_errorMat && Object.keys(_errorGroups).length > 0) {
      _pulseTick += 0.08;
      _errorMat.emissiveIntensity = 0.38 + 0.38 * Math.sin(_pulseTick);
    }

    // Gentle idle rotation (very slow)
    if (_fig.hips && _lerpT >= 1.0) {
      var tick = Date.now() * 0.0004;
      _fig.hips.rotation.y = Math.sin(tick) * 0.06;
    }

    if (_renderer && _scene && _camera) {
      _renderer.render(_scene, _camera);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // PUBLIC API
  // ══════════════════════════════════════════════════════════════════════════════

  function init(containerId) {
    if (_initialized) destroy();

    var container = document.getElementById(containerId);
    if (!container) {
      console.warn('Vyayam3D: container not found:', containerId);
      return;
    }

    var W = container.clientWidth  || 320;
    var H = container.clientHeight || 360;

    _scene = new THREE.Scene();
    _scene.background = new THREE.Color(0x0a0e1f);

    // Lighting
    _scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    var dir1 = new THREE.DirectionalLight(0x38bdf8, 1.1);
    dir1.position.set(1.5, 3, 2);
    _scene.add(dir1);
    var dir2 = new THREE.DirectionalLight(0xffffff, 0.45);
    dir2.position.set(-2, 2, -1);
    _scene.add(dir2);
    var fill = new THREE.DirectionalLight(0x6366f1, 0.35);
    fill.position.set(0, -1, 2);
    _scene.add(fill);

    // Camera
    _camera = new THREE.PerspectiveCamera(36, W / H, 0.01, 100);
    _camera.position.set(0, 1.0, 3.2);
    _camera.lookAt(0, 0.92, 0);

    // Renderer
    _renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    _renderer.setSize(W, H);
    _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    _renderer.outputEncoding = THREE.sRGBEncoding;
    _renderer.shadowMap.enabled = false;
    container.appendChild(_renderer.domElement);

    // Ground disc
    var ringGeo = new THREE.RingGeometry(0.22, 0.25, 32);
    var ringMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8, opacity: 0.18, transparent: true, side: THREE.DoubleSide
    });
    var ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = -PI / 2;
    ring.position.y = 0.002;
    _scene.add(ring);

    // Ground plane glow
    var planeGeo = new THREE.CircleGeometry(0.5, 32);
    var planeMat = new THREE.MeshBasicMaterial({
      color: 0x1e40af, opacity: 0.08, transparent: true, side: THREE.DoubleSide
    });
    var plane = new THREE.Mesh(planeGeo, planeMat);
    plane.rotation.x = -PI / 2;
    _scene.add(plane);

    // Error material reference
    _errorMat = new THREE.MeshStandardMaterial({
      color: 0xff3232, emissive: 0xff3232, emissiveIntensity: 0.55,
      roughness: 0.3, metalness: 0.3
    });

    // Build procedural figure
    buildFigure(_scene);

    _initialized = true;
    renderLoop();

    // Apply any pending pose
    if (_pendingPose) {
      _currentJoints  = _pendingPose.joints;
      _prevJoints     = {};
      _lerpDuration   = _pendingPose.duration;
      _lerpStart      = Date.now();
      _lerpT          = 0;
      _pendingPose    = null;
      applyPose(_currentJoints);
    }
  }

  function setPose(joints, duration) {
    if (!_initialized) {
      _pendingPose = { joints: joints || {}, duration: duration || 1200 };
      return;
    }
    _prevJoints   = {};
    Object.keys(_currentJoints).forEach(function (k) { _prevJoints[k] = _currentJoints[k]; });
    _currentJoints = joints || {};
    _lerpDuration  = duration || 1200;
    _lerpStart     = Date.now();
    _lerpT         = 0;
    resetAllMaterials();
  }

  function setError(errorJoints) {
    if (!_initialized) return;
    resetAllMaterials();
    if (!errorJoints || errorJoints.length === 0) return;
    errorJoints.forEach(function (jointKey) {
      var segs = JOINT_TO_SEGS[jointKey] || [];
      segs.forEach(function (segName) {
        setMaterialOnGroup(segName, _errorMat);
        _errorGroups[segName] = true;
      });
    });
  }

  function destroy() {
    if (_animId) { cancelAnimationFrame(_animId); _animId = null; }
    if (_renderer) {
      _renderer.dispose();
      var el = _renderer.domElement;
      if (el && el.parentNode) el.parentNode.removeChild(el);
    }
    if (_bodyMat)  { _bodyMat.dispose();  _bodyMat  = null; }
    if (_jointMat) { _jointMat.dispose(); _jointMat = null; }
    if (_errorMat) { _errorMat.dispose(); _errorMat = null; }
    _scene = null; _camera = null; _renderer = null;
    _fig = {}; _errorGroups = {};
    _currentJoints = {}; _prevJoints = {};
    _pendingPose = null; _pulseTick = 0;
    _lerpT = 1.0; _initialized = false;
  }

  window.Vyayam3D = { init: init, setPose: setPose, setError: setError, destroy: destroy };

}());
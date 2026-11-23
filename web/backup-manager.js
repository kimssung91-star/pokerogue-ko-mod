/*
 * Personal PokéRogue: download-based backup and restore.
 * Uses existing game localStorage values verbatim, with no external server.
 * Auto-downloads are best-effort because browsers can block unattended downloads.
 */
(() => {
  "use strict";

  const FORMAT = "pokerogue-ko-personal-backup";
  const VERSION = 1;
  const AUTO_KEY = "pkrBackupAutoEnabled";
  const LAST_AUTO_KEY = "pkrBackupLastRun";
  const BASE_KEYS = ["data_Guest", "runHistoryData_Guest", "settings", "tutorials", "mappingConfigs", "prLang"];
  const SESSION_KEY = /^sessionData(?:[1-4])?_Guest$/;
  const supportsFile = typeof Blob !== "undefined" && !!URL.createObjectURL;
  let lastError = "";
  let busy = false;
  let statusNode;
  let autoInput;

  function isGameKey(key) {
    return BASE_KEYS.includes(key) || SESSION_KEY.test(key);
  }

  // The official offline serializer is btoa(encodeURIComponent(JSON.stringify(...))).
  function decodeGameJson(raw) {
    return JSON.parse(decodeURIComponent(atob(raw)));
  }

  function getSessions(values) {
    const sessions = [];
    for (const [key, raw] of Object.entries(values)) {
      if (!SESSION_KEY.test(key)) continue;
      try {
        const save = decodeGameJson(raw);
        if (save && Array.isArray(save.party) && Number.isInteger(save.waveIndex) && save.waveIndex > 0) {
          sessions.push({
            key,
            wave: save.waveIndex,
            timestamp: Number(save.timestamp) || 0,
            seed: String(save.seed || "")
          });
        }
      } catch (_) {
        // An undecodable save is included in the file verbatim for manual recovery.
      }
    }
    return sessions;
  }

  function snapshot() {
    const values = Object.create(null);
    for (const key of Object.keys(localStorage)) {
      if (isGameKey(key)) {
        values[key] = localStorage.getItem(key);
      }
    }
    if (typeof values.data_Guest !== "string") {
      throw new Error("시스템 저장 데이터가 아직 없습니다. 게임 로딩 후 다시 시도하세요.");
    }
    const sessions = getSessions(values);
    sessions.sort((a, b) => b.timestamp - a.timestamp);
    return {
      format: FORMAT,
      version: VERSION,
      savedAt: new Date().toISOString(),
      origin: location.origin,
      path: location.pathname,
      latestWave: sessions[0]?.wave || 0,
      storage: values
    };
  }

  function filename(backup) {
    const date = backup.savedAt.replace(/[:.]/g, "-");
    return "PokeRogue_Backup_W" + String(backup.latestWave).padStart(3, "0") + "_" + date + ".json";
  }

  function show(message, isError = false) {
    if (statusNode) {
      statusNode.textContent = message;
      statusNode.style.color = isError ? "#ffb8b8" : "#d7f9e2";
    }
    if (isError) console.warn("[PokéRogue Backup]", message);
  }

  function download(backup) {
    if (!supportsFile) throw new Error("이 브라우저는 파일 다운로드를 지원하지 않습니다.");
    const blob = new Blob([JSON.stringify(backup)], { type: "application/json;charset=utf-8" });
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename(backup);
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    try {
      anchor.click();
    } finally {
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    }
    // We cannot detect a browser or enterprise policy blocking an automatic download.
    return backup.latestWave;
  }

  function backupNow() {
    try {
      const backup = snapshot();
      download(backup);
      show(backup.latestWave
        ? "웨이브 " + backup.latestWave + " 백업 다운로드를 요청했어요. 브라우저의 다운로드 목록에서 파일을 확인하세요."
        : "시스템 데이터 백업 다운로드를 요청했어요. 진행 중인 런 세이브는 없어요.");
      return backup;
    } catch (error) {
      show("백업 실패: " + error.message, true);
      return null;
    }
  }

  function validateBackup(backup) {
    if (!backup || backup.format !== FORMAT || backup.version !== VERSION
      || !backup.storage || typeof backup.storage !== "object" || Array.isArray(backup.storage)) {
      throw new Error("이 개조판에서 만든 백업 파일이 아닙니다.");
    }
    if (backup.origin !== location.origin) {
      throw new Error("다른 사이트에서 만든 백업입니다. 원래 사이트에서 복원하세요.");
    }
    const keys = Object.keys(backup.storage);
    if (!keys.includes("data_Guest") || keys.some(key => !isGameKey(key))) {
      throw new Error("저장 키가 올바르지 않습니다.");
    }
    for (const key of keys) {
      if (typeof backup.storage[key] !== "string") {
        throw new Error("저장 값 형식이 잘못되었습니다: " + key);
      }
    }
    const systemData = decodeGameJson(backup.storage.data_Guest);
    if (!systemData.dexData || !systemData.starterData || !systemData.timestamp) {
      throw new Error("시스템 저장 데이터가 손상되었습니다.");
    }
    for (const key of keys.filter(key => SESSION_KEY.test(key))) {
      const saved = decodeGameJson(backup.storage[key]);
      if (!Array.isArray(saved.party) || !Array.isArray(saved.enemyParty)
        || !Number.isInteger(saved.waveIndex) || saved.waveIndex < 1 || !saved.timestamp) {
        throw new Error("런 저장 데이터가 손상되었습니다: " + key);
      }
    }
    return backup.storage;
  }

  async function restoreFile(file) {
    if (!file) return;
    if (busy) return;
    busy = true;
    try {
      if (file.size > 30 * 1024 * 1024) throw new Error("백업 파일이 비정상적으로 큽니다.");
      const content = JSON.parse(await file.text());
      const restored = validateBackup(content);
      const sessions = getSessions(restored);
      const waves = sessions.map(s => s.wave).sort((a, b) => b - a);
      const details = waves.length ? ("진행 기록: " + waves.join(", ") + " 웨이브") : "런 기록 없음 (시스템 데이터만)";
      if (!window.confirm("백업을 복원할까요?\n" + details
        + "\n\n현재 브라우저의 게임 저장을 덮어씁니다. 원한다면 먼저 현재 데이터를 백업하세요.")) {
        return;
      }
      const rollback = Object.create(null);
      const keysToClear = new Set([...Object.keys(localStorage).filter(isGameKey), ...Object.keys(restored)]);
      for (const key of keysToClear) rollback[key] = localStorage.getItem(key);
      try {
        for (const key of keysToClear) localStorage.removeItem(key);
        for (const [key, value] of Object.entries(restored)) localStorage.setItem(key, value);
      } catch (error) {
        for (const key of keysToClear) {
          if (rollback[key] === null) localStorage.removeItem(key);
          else localStorage.setItem(key, rollback[key]);
        }
        throw error;
      }
      localStorage.removeItem(LAST_AUTO_KEY);
      show("복원했습니다. 게임을 새로고침합니다.");
      window.location.reload();
    } catch (error) {
      show("복원 실패: " + error.message, true);
    } finally {
      busy = false;
    }
  }

  function checkAutomaticBackup() {
    if (busy || localStorage.getItem(AUTO_KEY) !== "1") return;
    try {
      const backup = snapshot();
      const sessions = getSessions(backup.storage).sort((a, b) => b.timestamp - a.timestamp);
      const newest = sessions[0];
      if (!newest) return;
      const last = JSON.parse(localStorage.getItem(LAST_AUTO_KEY) || "null");
      const run = newest.key + ":" + newest.seed;
      // Every five waves, starting with a backup made when auto backup is enabled.
      if (last?.run === run && newest.wave < last.wave + 5) return;
      download(backup);
      localStorage.setItem(LAST_AUTO_KEY, JSON.stringify({ run, wave: newest.wave }));
      show("웨이브 " + newest.wave + " 자동 백업 요청 완료. 다운로드 목록에서 확인하세요.");
    } catch (error) {
      if (lastError !== error.message) {
        lastError = error.message;
        show("자동 백업 확인 필요: " + error.message, true);
      }
    }
  }

  function initialize() {
    const panel = document.createElement("div");
    panel.id = "pkr-personal-backup-ui";
    panel.style.cssText = "position:fixed;right:5px;top:5px;z-index:2147483647;color:#fff;font:12px/1.5 sans-serif;text-align:left;display:flex;flex-direction:column;align-items:flex-end";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.textContent = "💾";
    toggle.title = "백업 메뉴 (Alt+B)";
    toggle.setAttribute("aria-label", "포켓로그 백업 메뉴 열기");
    toggle.style.cssText = "width:24px;height:24px;padding:0;line-height:22px;font-size:13px;background:#243348;color:#fff;border:1px solid #d2e2f3;border-radius:5px;cursor:pointer;opacity:.22;transition:opacity .15s";
    toggle.setAttribute("aria-expanded", "false");
    const drawer = document.createElement("div");
    drawer.hidden = true;
    drawer.style.cssText = "width:min(310px,85vw);max-height:65vh;overflow:auto;background:#1a2534;border:1px solid #a3b3ca;border-radius:8px;padding:12px;box-shadow:0 4px 20px #0009;margin-top:5px;white-space:normal";
    drawer.innerHTML = '<strong style="font-size:14px">포켓로그 로컬 백업</strong><p style="margin:6px 0">브라우저 저장과 별도로 파일을 내려받고 복원합니다. 다운로드 폴더는 브라우저 설정을 따릅니다.</p>';
    const manual = document.createElement("button");
    manual.type = "button";
    manual.textContent = "현재 기록 백업 다운로드";
    manual.style.cssText = "display:block;width:100%;padding:8px;margin:5px 0;background:#277752;color:#fff;border:0;border-radius:5px;cursor:pointer";
    const restore = document.createElement("button");
    restore.type = "button";
    restore.textContent = "백업 파일 복원";
    restore.style.cssText = "display:block;width:100%;padding:8px;margin:5px 0;background:#4965a8;color:#fff;border:0;border-radius:5px;cursor:pointer";
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".json,application/json";
    fileInput.hidden = true;
    const label = document.createElement("label");
    label.style.cssText = "display:flex;align-items:center;gap:5px;margin:8px 0;cursor:pointer";
    autoInput = document.createElement("input");
    autoInput.type = "checkbox";
    autoInput.checked = localStorage.getItem(AUTO_KEY) === "1";
    label.append(autoInput, document.createTextNode("5웨이브마다 자동 다운로드 시도"));
    const help = document.createElement("p");
    help.textContent = "자동 다운로드는 Chrome에서 차단할 수 있어요. 사이트의 자동 다운로드를 허용하고, 파일이 실제로 생성되는지 확인하세요. 파일은 PC가 초기화되지 않는 폴더에 보관하세요.";
    help.style.cssText = "margin:5px 0;color:#cfdeef;font-size:11px";
    statusNode = document.createElement("div");
    statusNode.setAttribute("role", "status");
    statusNode.style.cssText = "font-size:11px;max-height:70px;overflow:auto;margin-top:8px;color:#d7f9e2";
    drawer.append(manual, restore, fileInput, label, help, statusNode);
    panel.append(toggle, drawer);
    document.body.appendChild(panel);

    panel.addEventListener("pointerdown", e => e.stopPropagation());
    panel.addEventListener("click", e => e.stopPropagation());
    panel.addEventListener("keydown", e => e.stopPropagation());
    function setDrawerOpen(open) {
      drawer.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      toggle.style.opacity = open ? ".94" : ".22";
    }
    toggle.addEventListener("click", () => { setDrawerOpen(drawer.hidden); });
    toggle.addEventListener("pointerenter", () => { toggle.style.opacity = ".94"; });
    toggle.addEventListener("pointerleave", () => {
      if (drawer.hidden) toggle.style.opacity = ".22";
    });
    document.addEventListener("pointerdown", event => {
      if (!drawer.hidden && !panel.contains(event.target)) setDrawerOpen(false);
    }, true);
    window.addEventListener("keydown", event => {
      // The backup interface must remain available without occupying game space.
      if (event.altKey && !event.ctrlKey && !event.metaKey && event.code === "KeyB") {
        event.preventDefault();
        event.stopImmediatePropagation();
        setDrawerOpen(drawer.hidden);
      } else if (event.code === "Escape" && !drawer.hidden) {
        event.preventDefault();
        event.stopImmediatePropagation();
        setDrawerOpen(false);
      }
    }, true);
    manual.addEventListener("click", () => {
      const b = backupNow();
      if (b && autoInput.checked) {
        const latest = getSessions(b.storage).sort((a, d) => d.timestamp - a.timestamp)[0];
        if (latest) localStorage.setItem(LAST_AUTO_KEY, JSON.stringify({ run: latest.key + ":" + latest.seed, wave: latest.wave }));
      }
    });
    restore.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0];
      fileInput.value = "";
      void restoreFile(file);
    });
    autoInput.addEventListener("change", () => {
      localStorage.setItem(AUTO_KEY, autoInput.checked ? "1" : "0");
      if (autoInput.checked) {
        // User gesture: request the first backup immediately so permissions can be granted.
        const b = backupNow();
        if (b) {
          const latest = getSessions(b.storage).sort((a, d) => d.timestamp - a.timestamp)[0];
          if (latest) localStorage.setItem(LAST_AUTO_KEY, JSON.stringify({ run: latest.key + ":" + latest.seed, wave: latest.wave }));
        }
      } else show("자동 파일 백업을 껐습니다. 수동 백업은 계속 사용할 수 있어요.");
    });
    setInterval(checkAutomaticBackup, 8000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();

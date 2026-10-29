# -*- coding: utf-8 -*-
"""Generate standalone, Modao-import-friendly HTML prototype pages."""
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "本地预览版"

COMMON_CSS = r"""
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: #eef2f7; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    color: #0f172a; font-size: 13px; line-height: 1.5; -webkit-font-smoothing: antialiased;
  }
  button { font-family: inherit; }
  a { text-decoration: none; color: inherit; }
  svg { flex-shrink: 0; display: block; }

  .app, .student-page, .teacher-shell, .login-page, .index-page { width: 1440px; height: 900px; overflow: hidden; }
  .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; }
  .muted { color: #64748b; }
  .strong { color: #334155; font-weight: 600; }
  .link { color: #2563eb; font-size: 11.5px; }
  .ml-auto { margin-left: auto; }
  .row { display: flex; align-items: center; }
  .between { display: flex; align-items: center; justify-content: space-between; }

  /* brand */
  .brand { display: flex; align-items: center; gap: 9px; }
  .logo { width: 30px; height: 30px; border-radius: 9px; background: #2563eb; display: flex; align-items: center; justify-content: center; }
  .brand-name { font-size: 15px; font-weight: 700; letter-spacing: .2px; color: #0f172a; }
  .brand-name.small { font-size: 13px; }
  .brand-sub { font-size: 9.5px; color: #94a3b8; margin-top: 1px; }
  .avatar { width: 32px; height: 32px; border-radius: 50%; background: #e0e7ff; color: #3730a3; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
  .avatar.sm { width: 28px; height: 28px; font-size: 10px; }
  .user-inline { display: flex; align-items: center; gap: 9px; }
  .user-name { font-size: 11.5px; font-weight: 600; color: #334155; }
  .user-role { font-size: 9.5px; color: #94a3b8; margin-top: 1px; }

  /* buttons */
  .btn { height: 36px; padding: 0 14px; border-radius: 8px; font-size: 12.5px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 7px; border: 1px solid transparent; background: #fff; color: #334155; }
  .btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
  .btn-secondary { background: #fff; color: #334155; border-color: #dbe2ea; }
  .btn-ghost { background: transparent; color: #475569; border-color: transparent; }
  .btn-danger { background: #dc2626; color: #fff; border-color: #dc2626; }
  .btn-sm { height: 30px; padding: 0 10px; font-size: 11px; border-radius: 7px; }
  .btn-block { width: 100%; }
  .icon-btn { width: 30px; height: 30px; border-radius: 7px; display: flex; align-items: center; justify-content: center; color: #64748b; background: #fff; border: 1px solid #eef2f7; }
  .icon-btn.plain { border-color: transparent; background: transparent; }

  /* chips / badges */
  .chip { display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 9px; border-radius: 6px; font-size: 11px; font-weight: 500; }
  .chip-blue { background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
  .chip-amber { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
  .chip-gray { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
  .badge { display: inline-flex; align-items: center; justify-content: center; height: 20px; padding: 0 7px; border-radius: 5px; font-size: 10px; font-weight: 600; white-space: nowrap; }
  .badge.green { background: #ecfdf5; color: #047857; }
  .badge.blue { background: #eff6ff; color: #1d4ed8; }
  .badge.amber { background: #fffbeb; color: #b45309; }
  .badge.red { background: #fef2f2; color: #b91c1c; }
  .badge.gray { background: #f1f5f9; color: #475569; }
  .badge.purple { background: #f5f3ff; color: #6d28d9; }

  /* cards */
  .card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; }
  .card-head { padding: 13px 16px; border-bottom: 1px solid #eef2f7; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .card-title { font-size: 13px; font-weight: 700; color: #0f172a; }
  .card-sub { font-size: 10px; color: #94a3b8; margin-top: 2px; }
  .card-body { padding: 16px; }

  /* page head */
  .page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
  .page-title { font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -.2px; line-height: 1.2; }
  .page-sub { font-size: 11.5px; color: #64748b; margin-top: 4px; }
  .page-actions { display: flex; align-items: center; gap: 9px; flex-shrink: 0; }

  /* stats */
  .stats-grid { display: flex; gap: 12px; margin-bottom: 14px; }
  .stat-card { flex: 1; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 13px 15px; display: flex; align-items: center; gap: 11px; }
  .stat-icon { width: 34px; height: 34px; border-radius: 9px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .stat-icon.green { background: #ecfdf5; color: #059669; }
  .stat-icon.amber { background: #fffbeb; color: #d97706; }
  .stat-icon.red { background: #fef2f2; color: #dc2626; }
  .stat-icon.purple { background: #f5f3ff; color: #7c3aed; }
  .stat-value { font-size: 19px; font-weight: 700; color: #0f172a; line-height: 1.1; }
  .stat-label { font-size: 10px; color: #64748b; margin-top: 3px; }
  .stat-trend { margin-left: auto; font-size: 9.5px; color: #94a3b8; }
  .stat-trend.green { color: #059669; }
  .stat-trend.red { color: #dc2626; }

  /* tables */
  .table { width: 100%; border-collapse: collapse; }
  .table th { height: 36px; padding: 0 12px; text-align: left; font-size: 10px; font-weight: 600; color: #64748b; background: #f8fafc; border-bottom: 1px solid #eef2f7; white-space: nowrap; }
  .table td { height: 52px; padding: 0 12px; font-size: 11.5px; color: #334155; border-bottom: 1px solid #f1f5f9; }
  .table tr:last-child td { border-bottom: none; }
  .table .sub { font-size: 9.5px; color: #94a3b8; margin-top: 2px; }
  .table-footer { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-top: 1px solid #eef2f7; font-size: 10px; color: #94a3b8; }
  .table-tools { display: flex; align-items: center; gap: 8px; }

  /* tabs */
  .tabs { display: flex; align-items: center; gap: 22px; border-bottom: 1px solid #e2e8f0; }
  .tab { height: 40px; display: flex; align-items: center; font-size: 12px; color: #64748b; border-bottom: 2px solid transparent; }
  .tab.active { color: #1d4ed8; font-weight: 600; border-bottom-color: #2563eb; }
  .tab-count { display: inline-flex; align-items: center; justify-content: center; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 4px; background: #f1f5f9; color: #64748b; font-size: 9px; margin-left: 4px; }

  /* forms */
  .field { display: flex; flex-direction: column; gap: 5px; }
  .label { font-size: 11px; color: #475569; font-weight: 600; }
  .input, .select { height: 36px; width: 100%; border: 1px solid #dbe2ea; border-radius: 8px; padding: 0 10px; font-size: 12px; color: #334155; background: #fff; display: flex; align-items: center; gap: 6px; }
  .select { justify-content: space-between; }
  .hint { font-size: 10px; color: #94a3b8; }
  .form-grid { display: flex; gap: 12px; }
  .form-grid.two > .field { width: 50%; }
  .form-grid.four > .field { width: 25%; }

  /* bars */
  .bar { height: 6px; border-radius: 3px; background: #eef2f7; overflow: hidden; }
  .bar-fill { display: block; height: 6px; border-radius: 3px; background: #2563eb; }
  .bar-fill.green { background: #059669; }
  .bar-fill.amber { background: #d97706; }
  .bar-fill.purple { background: #7c3aed; }
  .w-0 { width: 0%; } .w-10 { width: 10%; } .w-30 { width: 30%; } .w-60 { width: 60%; } .w-80 { width: 80%; } .w-82 { width: 82%; } .w-94 { width: 94%; }

  /* checks */
  .check-line { display: flex; align-items: center; gap: 7px; font-size: 10.5px; color: #475569; padding: 5px 0; }
  .check-line .ok { color: #059669; display: flex; }
  .check-line .warn { color: #d97706; display: flex; }
  .check-row { display: flex; align-items: flex-start; gap: 8px; font-size: 11px; color: #475569; line-height: 1.5; }
  .check-box { width: 14px; height: 14px; border-radius: 4px; border: 1.5px solid #cbd5e1; flex-shrink: 0; margin-top: 1px; display: flex; align-items: center; justify-content: center; }
  .check-box.checked { background: #2563eb; border-color: #2563eb; }

  /* timeline */
  .tl-item { display: flex; gap: 10px; padding-bottom: 12px; }
  .tl-item:last-child { padding-bottom: 0; }
  .tl-rail { width: 12px; display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
  .tl-dot { width: 8px; height: 8px; border-radius: 50%; background: #cbd5e1; margin-top: 4px; flex-shrink: 0; }
  .tl-dot.blue { background: #2563eb; }
  .tl-dot.green { background: #059669; }
  .tl-dot.amber { background: #d97706; }
  .tl-dot.red { background: #dc2626; }
  .tl-line { width: 1px; flex: 1; background: #e2e8f0; margin-top: 4px; }
  .tl-item:last-child .tl-line { display: none; }
  .tl-time { width: 38px; font-size: 9.5px; color: #94a3b8; flex-shrink: 0; padding-top: 1px; }
  .tl-content { flex: 1; }
  .tl-title { font-size: 11.5px; font-weight: 600; color: #334155; }
  .tl-desc { font-size: 10px; color: #64748b; margin-top: 2px; line-height: 1.5; }

  /* student nav */
  .student-nav { height: 64px; background: #fff; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between; padding: 0 32px; }
  .student-nav-left { display: flex; align-items: center; gap: 28px; }
  .nav-links { display: flex; align-items: center; gap: 24px; }
  .nav-link { font-size: 12px; color: #64748b; height: 64px; display: flex; align-items: center; border-bottom: 2px solid transparent; }
  .nav-link.active { color: #1d4ed8; font-weight: 600; border-bottom-color: #2563eb; }
  .student-nav-right { display: flex; align-items: center; gap: 10px; }
  .student-content { width: 1180px; margin-left: auto; margin-right: auto; padding: 22px 0; }

  /* teacher shell */
  .teacher-shell { display: flex; background: #f5f7fb; }
  .teacher-sidebar { width: 220px; background: #fff; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; flex-shrink: 0; }
  .teacher-brand { height: 64px; padding: 0 18px; display: flex; align-items: center; gap: 9px; border-bottom: 1px solid #eef2f7; }
  .side-nav { padding: 12px 10px; }
  .side-label { padding: 10px 10px 6px; font-size: 9.5px; font-weight: 600; color: #94a3b8; letter-spacing: .6px; }
  .side-link { height: 38px; padding: 0 10px; border-radius: 7px; display: flex; align-items: center; gap: 9px; font-size: 12px; color: #475569; }
  .side-link.active { background: #eff6ff; color: #1d4ed8; font-weight: 600; }
  .side-bottom { margin-top: auto; padding: 14px; border-top: 1px solid #eef2f7; }
  .teacher-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .teacher-topbar { height: 60px; background: #fff; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; flex-shrink: 0; }
  .breadcrumb { font-size: 11px; color: #94a3b8; display: flex; align-items: center; gap: 7px; }
  .breadcrumb .current { color: #334155; font-weight: 600; }
  .topbar-actions { display: flex; align-items: center; gap: 8px; }
  .search-box { height: 30px; width: 200px; border: 1px solid #dbe2ea; border-radius: 7px; display: flex; align-items: center; gap: 6px; padding: 0 9px; font-size: 10px; color: #94a3b8; background: #fff; }
  .teacher-content { flex: 1; min-height: 0; padding: 20px 24px; overflow: hidden; }
"""

ICONS = {
    "logo": '<path d="M4 7l4 5-4 5"/><path d="M12 17h8"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "folder": '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
    "file": '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z"/><path d="M14 3v5h5"/>',
    "document": '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6l7-3z"/><path d="M9.5 12l1.8 1.8 3.4-3.6"/>',
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "x-circle": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6"/><path d="M15 9l-6 6"/>',
    "alert": '<path d="M12 3L2 21h20L12 3z"/><path d="M12 9v5"/><path d="M12 18h.01"/>',
    "play": '<path d="M8 5l11 7-11 7V5z"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3"/><path d="M13 15h4"/>',
    "sparkles": '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z"/>',
    "history": '<path d="M3 12a9 9 0 109-9 9 9 0 00-7.5 4"/><path d="M3 3v6h6"/><path d="M12 7v5l3 2"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "send": '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/>',
    "at": '<circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 006 0v-1a10 10 0 10-3.9 7.9"/>',
    "paperclip": '<path d="M21.4 11.6l-8.5 8.5a5 5 0 01-7.1-7.1l9.2-9.2a3.5 3.5 0 014.9 4.9l-9.2 9.2a2 2 0 01-2.8-2.8l8.5-8.5"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
    "unlock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 017.5-2"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "bell": '<path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.2a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.2a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.2a1.7 1.7 0 001 1.5 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.2a1.7 1.7 0 00-1.5 1z"/>',
    "users": '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.9"/><path d="M16 3.1a4 4 0 010 7.8"/>',
    "user": '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 16v-5"/><path d="M12 16V7"/><path d="M17 16v-8"/>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
    "logout": '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    "plus": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/>',
    "refresh": '<path d="M21 12a9 9 0 11-2.6-6.4"/><path d="M21 3v6h-6"/>',
    "download": '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "filter": '<path d="M22 3H2l8 9.5V19l4 2v-8.5L22 3z"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
    "edit": '<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.1 2.1 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 1v3"/><path d="M15 1v3"/><path d="M9 20v3"/><path d="M15 20v3"/><path d="M1 9h3"/><path d="M1 15h3"/><path d="M20 9h3"/><path d="M20 15h3"/>',
    "wifi": '<path d="M5 12.5a10 10 0 0114 0"/><path d="M8.5 16a5.5 5.5 0 017 0"/><circle cx="12" cy="19.5" r=".5"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1v18"/>',
    "key": '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M11 12l9-9"/><path d="M15 4l4 4"/><path d="M18 7l2-2"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "clipboard": '<path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
}


def icon(name, size=16, color="currentColor", stroke=1.8):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        f"{ICONS[name]}</svg>"
    )


def badge(text, color="gray"):
    return f'<span class="badge {color}">{text}</span>'


def stat_card(icon_name, color, value, label, trend="", trend_class=""):
    trend_html = f'<span class="stat-trend {trend_class}">{trend}</span>' if trend else ""
    return f"""
    <div class="stat-card">
      <div class="stat-icon {color}">{icon(icon_name, 17)}</div>
      <div><div class="stat-value">{value}</div><div class="stat-label">{label}</div></div>
      {trend_html}
    </div>"""


def check_line(text, ok=True):
    if ok:
        return f'<div class="check-line"><span class="ok">{icon("check-circle",13,"#059669")}</span>{text}</div>'
    return f'<div class="check-line"><span class="warn">{icon("alert",13,"#d97706")}</span>{text}</div>'


def student_nav(active="exams"):
    def cls(key):
        return "nav-link active" if active == key else "nav-link"

    return f"""
  <header class="student-nav">
    <div class="student-nav-left">
      <div class="brand">
        <div class="logo">{icon("logo",17,"#ffffff",2.2)}</div>
        <div class="brand-name">AI Coding 考试平台</div>
      </div>
      <nav class="nav-links">
        <a class="{cls("exams")}" href="02-exam-list.html">我的考试</a>
        <a class="{cls("reports")}" href="06-report.html">成绩报告</a>
        <a class="{cls("help")}" href="03-precheck.html">考试须知</a>
      </nav>
    </div>
    <div class="student-nav-right">
      <span class="icon-btn plain">{icon("search",16)}</span>
      <span class="icon-btn plain">{icon("bell",16)}</span>
      <div class="user-inline">
        <div class="avatar sm">李</div>
        <div><div class="user-name">李同学</div><div class="user-role">考生 · 2023012345</div></div>
      </div>
    </div>
  </header>"""


def teacher_sidebar(active="exams"):
    def cls(key):
        return "side-link active" if active == key else "side-link"

    return f"""
  <aside class="teacher-sidebar">
    <div class="teacher-brand">
      <div class="logo">{icon("logo",17,"#ffffff",2.2)}</div>
      <div><div class="brand-name small">AI Coding</div><div class="brand-sub">考试平台 · 教师端</div></div>
    </div>
    <div class="side-nav">
      <div class="side-label">工作台</div>
      <a class="{cls("exams")}" href="07-exam-manage.html">{icon("document",16)}考试管理</a>
      <a class="{cls("bank")}" href="#">{icon("book",16)}题库管理</a>
      <a class="{cls("grades")}" href="#">{icon("chart",16)}成绩分析</a>
      <a class="{cls("proctor")}" href="10-proctor.html">{icon("monitor",16)}监考中心</a>
      <div class="side-label">配置</div>
      <a class="{cls("students")}" href="#">{icon("users",16)}考生名单</a>
      <a class="{cls("images")}" href="#">{icon("database",16)}镜像与资源</a>
      <a class="{cls("settings")}" href="#">{icon("settings",16)}系统设置</a>
    </div>
    <div class="side-bottom">
      <div class="user-inline">
        <div class="avatar sm">刘</div>
        <div><div class="user-name">刘老师</div><div class="user-role">命题人 · 软件学院</div></div>
        <span class="icon-btn plain ml-auto">{icon("logout",15)}</span>
      </div>
    </div>
  </aside>"""


def teacher_topbar(title, crumb):
    return f"""
  <header class="teacher-topbar">
    <div class="breadcrumb">
      <span>工作台</span>{icon("chevron-right",12,"#cbd5e1")}
      <span>{crumb}</span>{icon("chevron-right",12,"#cbd5e1")}
      <span class="current">{title}</span>
    </div>
    <div class="topbar-actions">
      <span class="search-box">{icon("search",14)}搜索考试、题目或考生</span>
      <span class="icon-btn plain">{icon("bell",16)}</span>
      <span class="icon-btn plain">{icon("settings",16)}</span>
      <div class="avatar sm">刘</div>
    </div>
  </header>"""


def doc(title, body, extra_css=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1440">
<title>{title}</title>
<style>
{COMMON_CSS}
{extra_css}
</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 01 登录
# ---------------------------------------------------------------------------
LOGIN_CSS = r"""
  .login-page { background: #f5f7fb; display: flex; flex-direction: column; padding: 0 40px; }
  .login-top { height: 78px; display: flex; align-items: center; justify-content: space-between; }
  .login-top-right { display: flex; align-items: center; gap: 8px; font-size: 11px; color: #94a3b8; }
  .login-wrap { flex: 1; display: flex; align-items: center; justify-content: center; }
  .login-card { width: 440px; background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 34px 38px 30px; box-shadow: 0 14px 34px rgba(15,23,42,.05); }
  .login-title { font-size: 24px; font-weight: 700; color: #0f172a; }
  .login-sub { font-size: 11.5px; color: #64748b; margin-top: 5px; }
  .role-tabs { display: flex; background: #f1f5f9; border-radius: 8px; padding: 3px; margin: 20px 0 18px; }
  .role-tab { flex: 1; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 11.5px; color: #64748b; border-radius: 6px; }
  .role-tab.active { background: #fff; color: #1d4ed8; font-weight: 600; box-shadow: 0 1px 2px rgba(15,23,42,.08); }
  .login-card .field { margin-bottom: 13px; }
  .login-card .input { height: 38px; font-size: 12px; color: #334155; }
  .login-card .btn-block { height: 40px; }
  .login-row { display: flex; align-items: center; justify-content: space-between; margin: 1px 0 16px; }
  .login-divider { display: flex; align-items: center; gap: 10px; margin: 16px 0; color: #94a3b8; font-size: 10px; }
  .login-divider .line { height: 1px; background: #e2e8f0; flex: 1; }
  .login-note { margin-top: 11px; text-align: center; font-size: 10px; color: #94a3b8; }
  .login-foot { margin-top: 16px; text-align: center; font-size: 9.5px; color: #94a3b8; line-height: 1.6; }
  .login-bottom { text-align: center; font-size: 9.5px; color: #a8b3c2; padding: 16px 0 18px; }
"""


LOGIN_ROLES = {
    "student": {
        "sub": "使用课程账号进入考试或工作台",
        "target": "02-exam-list.html",
        "note": "当前身份：学生 · 登录后进入我的考试",
    },
    "teacher": {
        "sub": "使用教师账号进入命题与监考工作台",
        "target": "07-exam-manage.html",
        "note": "当前身份：教师 · 登录后进入考试管理",
    },
    "admin": {
        "sub": "使用管理员账号进入平台管理",
        "target": "07-exam-manage.html",
        "note": "当前身份：管理员 · 登录后进入考试管理",
    },
}


def page_login(role="student"):
    cfg = LOGIN_ROLES[role]

    def cls(key):
        return "role-tab active" if key == role else "role-tab"

    body = f"""
<div class="login-page">
  <div class="login-top">
    <div class="brand">
      <div class="logo">{icon("logo",17,"#ffffff",2.2)}</div>
      <div class="brand-name">AI Coding 考试平台</div>
    </div>
    <div class="login-top-right">
      <span>帮助中心</span><span>·</span><span>隐私说明</span>
    </div>
  </div>

  <div class="login-wrap">
    <div class="login-card">
      <div class="login-title">登录</div>
      <div class="login-sub">{cfg["sub"]}</div>
      <div class="role-tabs">
        <a class="{cls("student")}" href="01-login.html">学生</a>
        <a class="{cls("teacher")}" href="01-login-teacher.html">教师</a>
        <a class="{cls("admin")}" href="01-login-admin.html">管理员</a>
      </div>
      <div class="field"><div class="label">学号 / 工号</div><div class="input">2023012345</div></div>
      <div class="field"><div class="label">密码</div><div class="input">••••••••</div></div>
      <div class="login-row">
        <span class="check-row"><span class="check-box checked">{icon("check",9,"#ffffff",3)}</span>记住我</span>
        <span class="link">忘记密码？</span>
      </div>
      <a class="btn btn-primary btn-block" href="{cfg["target"]}">登录</a>
      <div class="login-note">{cfg["note"]}</div>
      <div class="login-foot">登录即表示同意《考试诚信与数据使用说明》</div>
    </div>
  </div>

  <div class="login-bottom">清华大学软件学院 · 软件工程课程项目 · 原型 V0.1</div>
</div>"""
    return body, LOGIN_CSS


# ---------------------------------------------------------------------------
# 02 考试列表
# ---------------------------------------------------------------------------
EXAM_LIST_CSS = r"""
  .date-text { display: flex; align-items: center; gap: 6px; font-size: 10.5px; color: #94a3b8; margin-right: 2px; }
  .exam-hero { background: #fff; border: 1px solid #dbeafe; border-left: 4px solid #2563eb; border-radius: 12px; padding: 18px 22px; display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 13px; }
  .hero-label { display: flex; align-items: center; gap: 6px; font-size: 10px; font-weight: 700; color: #1d4ed8; letter-spacing: .4px; }
  .live-dot { width: 6px; height: 6px; border-radius: 50%; background: #2563eb; }
  .hero-title { font-size: 19px; font-weight: 700; color: #0f172a; margin-top: 5px; }
  .hero-meta { display: flex; align-items: center; gap: 15px; margin-top: 7px; font-size: 10.5px; color: #64748b; }
  .hero-meta span { display: flex; align-items: center; gap: 5px; }
  .hero-note { font-size: 10px; color: #94a3b8; margin-top: 7px; }
  .exam-hero-right { text-align: right; flex-shrink: 0; }
  .countdown-label { font-size: 9.5px; color: #94a3b8; }
  .countdown { font-size: 25px; font-weight: 700; color: #0f172a; letter-spacing: .5px; margin: 2px 0 8px; }
  .exam-main { display: flex; gap: 13px; }
  .exam-list-card { flex: 1; min-width: 0; }
  .side-col { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .tabs-inline { display: flex; gap: 3px; background: #f1f5f9; border-radius: 7px; padding: 3px; }
  .tab-pill { height: 23px; padding: 0 9px; border-radius: 5px; font-size: 10px; color: #64748b; display: flex; align-items: center; }
  .tab-pill.active { background: #fff; color: #1d4ed8; font-weight: 600; }
  .rule-item { display: flex; gap: 9px; padding: 7px 0; border-bottom: 1px solid #f1f5f9; }
  .rule-item:last-child { border-bottom: none; padding-bottom: 0; }
  .rule-num { width: 18px; height: 18px; border-radius: 50%; background: #eff6ff; color: #1d4ed8; font-size: 9px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }
  .rule-title { font-size: 10.5px; font-weight: 600; color: #334155; }
  .rule-desc { font-size: 9.5px; color: #64748b; margin-top: 2px; line-height: 1.5; }
  .check-line.device { padding: 5px 0; font-size: 10.5px; }
  .recent-box { padding: 11px 16px 13px; border-top: 1px solid #eef2f7; }
  .recent-label { font-size: 10px; font-weight: 600; color: #64748b; margin-bottom: 7px; }
  .recent-chips { display: flex; gap: 8px; }
  .recent-chip { flex: 1; background: #f8fafc; border: 1px solid #eef2f7; border-radius: 7px; padding: 8px 9px; font-size: 9.5px; color: #64748b; display: flex; align-items: center; justify-content: space-between; }
  .recent-chip strong { font-size: 14px; color: #0f172a; }
"""


def page_exam_list():
    rows = """
        <tr>
          <td><div class="strong">软件工程 · 期中机考</div><div class="sub">3 道工程题 · 45 人</div></td>
          <td>10-25 14:00</td>
          <td>120 分钟</td>
          <td>受限</td>
          <td><span class="badge blue">待考</span></td>
          <td class="muted">—</td>
          <td><a class="link" href="03-precheck.html">进入考场</a></td>
        </tr>
        <tr>
          <td><div class="strong">数据结构 · 随堂测验 3</div><div class="sub">2 道算法题 · 42 人</div></td>
          <td>10-18 10:00</td>
          <td>45 分钟</td>
          <td>关闭</td>
          <td><span class="badge gray">已完成</span></td>
          <td><span class="strong">92</span></td>
          <td><a class="link" href="06-report.html">查看报告</a></td>
        </tr>
        <tr>
          <td><div class="strong">算法设计 · 单元测试</div><div class="sub">1 道工程题 · 38 人</div></td>
          <td>10-11 14:00</td>
          <td>60 分钟</td>
          <td>开放</td>
          <td><span class="badge gray">已完成</span></td>
          <td><span class="strong">88</span></td>
          <td><a class="link" href="06-report.html">查看报告</a></td>
        </tr>
        <tr>
          <td><div class="strong">软件工程 · 作业 2</div><div class="sub">1 道工程题 · 45 人</div></td>
          <td>09-27 19:00</td>
          <td>90 分钟</td>
          <td>受限</td>
          <td><span class="badge gray">已完成</span></td>
          <td><span class="strong">80</span></td>
          <td><a class="link" href="06-report.html">查看报告</a></td>
        </tr>"""

    body = f"""
<div class="student-page">
  {student_nav("exams")}
  <div class="student-content">
    <div class="page-head">
      <div><div class="page-title">我的考试</div><div class="page-sub">查看考试安排、进入考场与历史成绩</div></div>
      <div class="page-actions">
        <span class="date-text">{icon("calendar",13)}2026年10月25日 周日</span>
        <a class="btn btn-secondary" href="03-precheck.html">考试须知</a>
      </div>
    </div>

    <div class="exam-hero">
      <div class="exam-hero-left">
        <div class="hero-label"><span class="live-dot"></span>即将开始</div>
        <div class="hero-title">软件工程 · 期中机考</div>
        <div class="hero-meta">
          <span>{icon("calendar",13)}10月25日 14:00–16:00</span>
          <span>{icon("clock",13)}120 分钟</span>
          <span>{icon("shield",13)}AI 受限模式</span>
          <span>{icon("document",13)}3 道工程题</span>
        </div>
        <div class="hero-note">建议提前 15 分钟完成环境自检；开考 15 分钟后禁止入场。</div>
      </div>
      <div class="exam-hero-right">
        <div class="countdown-label">距开始</div>
        <div class="countdown">00:27:18</div>
        <a class="btn btn-primary" href="03-precheck.html">{icon("arrow-right",14)}进入考场</a>
      </div>
    </div>

    <div class="stats-grid">
      {stat_card("calendar","", "1", "待考考试")}
      {stat_card("check-circle","green", "3", "已完成考试")}
      {stat_card("chart","purple", "86.7", "平均分", "较上次 +4.2", "green")}
    </div>

    <div class="exam-main">
      <div class="card exam-list-card">
        <div class="card-head">
          <div><div class="card-title">全部考试</div><div class="card-sub">共 4 场考试</div></div>
          <div class="tabs-inline"><span class="tab-pill active">全部</span><span class="tab-pill">待考</span><span class="tab-pill">已完成</span></div>
        </div>
        <table class="table">
          <thead><tr><th>考试</th><th>时间</th><th>时长</th><th>AI 模式</th><th>状态</th><th>成绩</th><th></th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <div class="recent-box">
          <div class="recent-label">最近成绩</div>
          <div class="recent-chips">
            <span class="recent-chip">数据结构 · 随堂测验 3 <strong>92</strong></span>
            <span class="recent-chip">算法设计 · 单元测试 <strong>88</strong></span>
            <span class="recent-chip">软件工程 · 作业 2 <strong>80</strong></span>
          </div>
        </div>
      </div>

      <div class="side-col">
        <div class="card">
          <div class="card-head"><div class="card-title">考试须知</div><span class="badge amber">请提前阅读</span></div>
          <div class="card-body">
            <div class="rule-item"><span class="rule-num">1</span><div><div class="rule-title">提前完成自检</div><div class="rule-desc">建议提前 15 分钟检查浏览器、网络、终端与 Agent。</div></div></div>
            <div class="rule-item"><span class="rule-num">2</span><div><div class="rule-title">AI 受限模式</div><div class="rule-desc">可解释与运行测试，不可直接写入代码；全程留痕。</div></div></div>
            <div class="rule-item"><span class="rule-num">3</span><div><div class="rule-title">网络与数据</div><div class="rule-desc">考试期间禁止外部网络；不录屏、不采集摄像头。</div></div></div>
            <div class="rule-item"><span class="rule-num">4</span><div><div class="rule-title">申诉时限</div><div class="rule-desc">成绩发布后 48 小时内可发起申诉，逾期不再受理。</div></div></div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div class="card-title">设备检查</div><span class="badge green">全部通过</span></div>
          <div class="card-body">
            {check_line("浏览器 · Chrome 128")}
            {check_line("网络 · 下行 86 Mbps")}
            {check_line("终端 · xterm.js 已连接")}
            {check_line("Coding Agent · 受限模式可用")}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, EXAM_LIST_CSS


# ---------------------------------------------------------------------------
# 03 环境自检
# ---------------------------------------------------------------------------
PRECHECK_CSS = r"""
  .stepper { display: flex; align-items: center; gap: 12px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 13px 20px; margin-bottom: 13px; }
  .step { display: flex; align-items: center; gap: 9px; }
  .step-num { width: 26px; height: 26px; border-radius: 50%; background: #f1f5f9; color: #64748b; font-size: 10.5px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
  .step.done .step-num { background: #059669; color: #fff; }
  .step.active .step-num { background: #2563eb; color: #fff; }
  .step-title { font-size: 11px; font-weight: 600; color: #334155; }
  .step-sub { font-size: 9.5px; color: #94a3b8; margin-top: 1px; }
  .step-line { flex: 1; height: 1px; background: #e2e8f0; }
  .precheck-main { display: flex; gap: 13px; }
  .precheck-card { flex: 1; min-width: 0; }
  .precheck-side { width: 360px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .check-item { display: flex; align-items: center; gap: 11px; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
  .check-item.last { border-bottom: none; }
  .ci-icon { width: 34px; height: 34px; border-radius: 9px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .ci-icon.green { background: #ecfdf5; color: #059669; }
  .ci-icon.purple { background: #f5f3ff; color: #7c3aed; }
  .ci-title { font-size: 11.5px; font-weight: 600; color: #334155; }
  .ci-desc { font-size: 10px; color: #64748b; margin-top: 2px; }
  .ci-main { flex: 1; }
  .precheck-actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
  .info-title { font-size: 13.5px; font-weight: 700; color: #0f172a; margin-bottom: 9px; }
  .info-row { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 10.5px; color: #64748b; }
  .info-row:last-child { border-bottom: none; }
  .info-row strong { color: #334155; font-weight: 600; }
  .privacy-note { display: flex; align-items: flex-start; gap: 6px; background: #f8fafc; border: 1px solid #eef2f7; border-radius: 7px; padding: 8px 9px; font-size: 9.5px; line-height: 1.5; color: #64748b; margin: 9px 0 11px; }
  .enter-hint { text-align: center; margin-top: 8px; }
"""


def page_precheck():
    body = f"""
<div class="student-page">
  {student_nav("exams")}
  <div class="student-content">
    <div class="page-head">
      <div><div class="page-title">进入考场</div><div class="page-sub">软件工程 · 期中机考 · 请完成考试须知阅读与环境自检</div></div>
      <div class="page-actions"><a class="btn btn-ghost" href="02-exam-list.html">{icon("arrow-left",14)}返回我的考试</a></div>
    </div>

    <div class="stepper">
      <div class="step done"><span class="step-num">{icon("check",11,"#ffffff",3)}</span><div><div class="step-title">阅读须知</div><div class="step-sub">已完成</div></div></div>
      <div class="step-line"></div>
      <div class="step active"><span class="step-num">2</span><div><div class="step-title">环境自检</div><div class="step-sub">进行中</div></div></div>
      <div class="step-line"></div>
      <div class="step"><span class="step-num">3</span><div><div class="step-title">进入考场</div><div class="step-sub">等待自检</div></div></div>
    </div>

    <div class="precheck-main">
      <div class="card precheck-card">
        <div class="card-head">
          <div><div class="card-title">环境自检</div><div class="card-sub">最近检测 14:02:18 · 全部项目通过</div></div>
          <span class="badge green">6 / 6 通过</span>
        </div>
        <div class="card-body">
          <div class="check-item">
            <div class="ci-icon">{icon("monitor",17)}</div>
            <div class="ci-main"><div class="ci-title">浏览器</div><div class="ci-desc">Chrome 128 · 分辨率 1440×900 · 支持最近两个版本</div></div>
            <span class="badge green">通过</span>
          </div>
          <div class="check-item">
            <div class="ci-icon">{icon("wifi",17)}</div>
            <div class="ci-main"><div class="ci-title">网络</div><div class="ci-desc">下行 86 Mbps / 上行 12 Mbps · 延迟 18 ms</div></div>
            <span class="badge green">通过</span>
          </div>
          <div class="check-item">
            <div class="ci-icon green">{icon("cpu",17)}</div>
            <div class="ci-main"><div class="ci-title">隔离容器</div><div class="ci-desc">容器 c-7f3a 已就绪 · 2 vCPU / 4 GB · 初始仓库已挂载</div></div>
            <span class="badge green">通过</span>
          </div>
          <div class="check-item">
            <div class="ci-icon">{icon("terminal",17)}</div>
            <div class="ci-main"><div class="ci-title">编辑器与终端</div><div class="ci-desc">Monaco Editor、xterm.js 连接正常 · Python 3.11</div></div>
            <span class="badge green">通过</span>
          </div>
          <div class="check-item">
            <div class="ci-icon purple">{icon("sparkles",17)}</div>
            <div class="ci-main"><div class="ci-title">Coding Agent</div><div class="ci-desc">受限模式 · 网关连接正常 · 对话将全程留痕</div></div>
            <span class="badge green">通过</span>
          </div>
          <div class="check-item last">
            <div class="ci-icon">{icon("shield",17)}</div>
            <div class="ci-main"><div class="ci-title">考试策略</div><div class="ci-desc">网络隔离已开启 · 自动保存 30s · 提交次数 2 次</div></div>
            <span class="badge green">通过</span>
          </div>
          <div class="precheck-actions">
            <span class="btn btn-secondary">{icon("refresh",14)}重新检测</span>
            <span class="hint">检测不会修改你的代码；如失败，请重试或联系监考。</span>
          </div>
        </div>
      </div>

      <div class="precheck-side">
        <div class="card">
          <div class="card-head"><div class="card-title">考试信息</div></div>
          <div class="card-body">
            <div class="info-title">软件工程 · 期中机考</div>
            <div class="info-row"><span>考试时间</span><strong>10月25日 14:00–16:00</strong></div>
            <div class="info-row"><span>考试时长</span><strong>120 分钟</strong></div>
            <div class="info-row"><span>题目数量</span><strong>3 道工程题</strong></div>
            <div class="info-row"><span>AI 模式</span><strong>受限模式</strong></div>
            <div class="info-row"><span>提交次数</span><strong>2 次</strong></div>
            <div class="info-row"><span>成绩规则</span><strong>取最高分</strong></div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><div class="card-title">考试承诺</div></div>
          <div class="card-body">
            <div class="check-row"><span class="check-box checked">{icon("check",9,"#ffffff",3)}</span><span>我已阅读并同意《考试诚信承诺》与《数据使用说明》。</span></div>
            <div class="privacy-note">{icon("shield",13)}本场考试不录屏、不采集摄像头；仅记录平台内操作与 AI 对话。</div>
            <a class="btn btn-primary btn-block" href="04-workbench.html">{icon("arrow-right",14)}进入考场</a>
            <div class="hint enter-hint">进入后计时立即开始</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, PRECHECK_CSS


# ---------------------------------------------------------------------------
# 05 提交结果
# ---------------------------------------------------------------------------
RESULT_CSS = r"""
  .result-summary { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 22px; display: flex; gap: 30px; margin-bottom: 13px; }
  .score-block { width: 290px; flex-shrink: 0; }
  .score-label { font-size: 10px; color: #94a3b8; }
  .score-value { font-size: 40px; font-weight: 700; color: #0f172a; line-height: 1.1; margin-top: 2px; }
  .score-value span { font-size: 13px; color: #94a3b8; font-weight: 500; }
  .score-status { display: flex; gap: 6px; margin: 7px 0; }
  .score-bar { height: 7px; border-radius: 4px; background: #eef2f7; overflow: hidden; }
  .score-fill { display: block; width: 82%; height: 7px; background: #2563eb; border-radius: 4px; }
  .score-note { font-size: 9.5px; color: #94a3b8; margin-top: 6px; }
  .score-metrics { flex: 1; display: flex; align-items: center; }
  .metric { flex: 1; text-align: center; border-left: 1px solid #eef2f7; padding: 7px 0; }
  .metric.first { border-left: none; }
  .metric-value { font-size: 19px; font-weight: 700; color: #0f172a; }
  .metric-value.green { color: #059669; }
  .metric-value.amber { color: #d97706; }
  .metric-label { font-size: 10px; color: #64748b; margin-top: 3px; }
  .result-main { display: flex; gap: 13px; }
  .result-table-card { flex: 1; min-width: 0; }
  .result-table-card .table td { height: 42px; }
  .result-table-card .table th { height: 34px; }
  .result-side { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .table-foot { display: flex; align-items: center; gap: 6px; padding: 9px 16px; font-size: 10px; color: #b45309; background: #fffbeb; border-top: 1px solid #fde68a; }
  .submit-item { display: flex; align-items: center; gap: 9px; padding: 8px 0; border-bottom: 1px solid #f1f5f9; }
  .submit-item.last { border-bottom: none; }
  .submit-dot { width: 8px; height: 8px; border-radius: 50%; background: #2563eb; flex-shrink: 0; }
  .submit-dot.gray { background: #cbd5e1; }
  .submit-title { font-size: 11px; font-weight: 600; color: #334155; }
  .submit-time { font-size: 9.5px; color: #94a3b8; margin-top: 2px; }
  .submit-item .badge { margin-left: auto; }
  .submit-rule { display: flex; align-items: flex-start; gap: 5px; margin-top: 8px; font-size: 9.5px; color: #94a3b8; line-height: 1.5; }
  .appeal-note { margin-top: 8px; font-size: 9.5px; color: #94a3b8; line-height: 1.5; text-align: center; }
  .gap-8 { height: 8px; }
  .score-rule { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #f1f5f9; font-size: 10px; color: #64748b; }
  .score-rule.last { border-bottom: none; }
  .score-rule strong { color: #334155; }
  .score-rule-note { font-size: 9px; color: #94a3b8; line-height: 1.5; margin-top: 5px; }
"""


def page_result():
    def row(name, kind, ok, t, mem):
        status = '<span class="badge green">通过</span>' if ok else '<span class="badge red">失败</span>'
        return f"<tr><td>{name}</td><td>{kind}</td><td>{status}</td><td>{t}</td><td>{mem}</td></tr>"

    rows = "".join([
        row("test_sort_basic", "样例", True, "0.12s", "12 MB"),
        row("test_sort_ties", "样例", True, "0.10s", "11 MB"),
        row("test_sort_iso_format", "样例", True, "0.11s", "12 MB"),
        row("test_sort_empty", "样例", True, "0.08s", "10 MB"),
        row("test_sort_single", "样例", True, "0.07s", "10 MB"),
        row("隐藏用例 #07", "隐藏", True, "0.18s", "16 MB"),
        row("隐藏用例 #08", "隐藏", False, "0.20s", "18 MB"),
        row("隐藏用例 #09", "隐藏", True, "0.17s", "15 MB"),
        row("隐藏用例 #10", "隐藏", False, "0.19s", "17 MB"),
    ])

    body = f"""
<div class="student-page">
  {student_nav("exams")}
  <div class="student-content">
    <div class="page-head">
      <div><div class="page-title">提交结果</div><div class="page-sub">软件工程 · 期中机考 · 第 2 次提交 · 14:58:32</div></div>
      <div class="page-actions">
        <a class="btn btn-secondary" href="04-workbench.html">{icon("arrow-left",14)}返回工作台</a>
        <a class="btn btn-primary" href="06-report.html">{icon("document",14)}查看过程报告</a>
      </div>
    </div>

    <div class="result-summary">
      <div class="score-block">
        <div class="score-label">当前总分</div>
        <div class="score-value">82<span> / 100</span></div>
        <div class="score-status"><span class="badge green">已提交</span><span class="badge amber">过程分待复核</span></div>
        <div class="score-bar"><span class="score-fill"></span></div>
        <div class="score-note">成绩规则：取最高分 · 当前为第 2 次提交（最高分）</div>
      </div>
      <div class="score-metrics">
        <div class="metric first"><div class="metric-value green">10/10</div><div class="metric-label">样例测试</div></div>
        <div class="metric"><div class="metric-value">8/10</div><div class="metric-label">隐藏测试</div></div>
        <div class="metric"><div class="metric-value">良好</div><div class="metric-label">代码质量</div></div>
        <div class="metric"><div class="metric-value amber">待评</div><div class="metric-label">AI 协作过程</div></div>
      </div>
    </div>

    <div class="result-main">
      <div class="card result-table-card">
        <div class="card-head">
          <div><div class="card-title">用例结果</div><div class="card-sub">隐藏用例仅显示汇总结果，不展示输入与预期输出</div></div>
          <span class="badge gray">共 20 个用例</span>
        </div>
        <table class="table">
          <thead><tr><th>用例</th><th>类型</th><th>结果</th><th>耗时</th><th>内存</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <div class="table-foot">{icon("alert",12)}2 个隐藏用例未通过：边界条件与异常输入。可返回工作台继续修改。</div>
      </div>

      <div class="result-side">
        <div class="card">
          <div class="card-head"><div class="card-title">提交记录</div><span class="badge blue">剩余 1 次</span></div>
          <div class="card-body">
            <div class="submit-item">
              <div class="submit-dot"></div>
              <div><div class="submit-title">第 2 次 · 82 分</div><div class="submit-time">14:58:32 · 当前最高分</div></div>
              <span class="badge green">最高</span>
            </div>
            <div class="submit-item last">
              <div class="submit-dot gray"></div>
              <div><div class="submit-title">第 1 次 · 64 分</div><div class="submit-time">14:36:10</div></div>
            </div>
            <div class="submit-rule">{icon("clock",11)}成绩取最高分；提交次数用尽后仍可查看结果。</div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><div class="card-title">下一步</div></div>
          <div class="card-body">
            <a class="btn btn-primary btn-block" href="04-workbench.html">继续修改并提交</a>
            <div class="gap-8"></div>
            <a class="btn btn-secondary btn-block" href="06-report.html">查看完整过程报告</a>
            <div class="appeal-note">对判分有异议？可在考试结束后 48 小时内发起申诉。</div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><div class="card-title">评分说明</div></div>
          <div class="card-body">
            <div class="score-rule"><span>测试用例</span><strong>70%</strong></div>
            <div class="score-rule"><span>AI 协作过程</span><strong>20%</strong></div>
            <div class="score-rule last"><span>教师复核</span><strong>10%</strong></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, RESULT_CSS


# ---------------------------------------------------------------------------
# 06 过程报告
# ---------------------------------------------------------------------------
REPORT_CSS = r"""
  .report-tabs { display: flex; gap: 24px; border-bottom: 1px solid #e2e8f0; margin-bottom: 13px; }
  .report-tabs .tab { height: 37px; }
  .report-summary { display: flex; align-items: center; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 20px; gap: 26px; margin-bottom: 13px; }
  .rs-score { width: 175px; flex-shrink: 0; }
  .rs-label { font-size: 9.5px; color: #94a3b8; }
  .rs-value { font-size: 32px; font-weight: 700; color: #0f172a; line-height: 1.1; }
  .rs-value span { font-size: 11px; color: #94a3b8; font-weight: 500; }
  .rs-note { font-size: 9px; color: #b45309; margin-top: 3px; }
  .rs-item { flex: 1; }
  .rs-item-label { font-size: 10px; color: #64748b; }
  .rs-item-value { font-size: 15px; font-weight: 700; color: #0f172a; margin: 2px 0 5px; }
  .rs-item-value span { font-size: 9.5px; color: #94a3b8; font-weight: 500; }
  .rs-item-value.amber { color: #d97706; }
  .report-main { display: flex; gap: 13px; }
  .report-timeline-card { flex: 1; min-width: 0; }
  .report-side { width: 360px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .rubric-item { margin-bottom: 8px; }
  .rubric-item.last { margin-bottom: 0; }
  .rubric-row { display: flex; justify-content: space-between; font-size: 10px; color: #475569; margin-bottom: 4px; }
  .rubric-row strong { color: #334155; }
  .rubric-ev { font-size: 9px; color: #94a3b8; margin-top: 3px; }
  .stats-mini { display: flex; flex-wrap: wrap; }
  .stats-mini > div { width: 50%; display: flex; justify-content: space-between; padding: 6px 0; font-size: 10px; color: #64748b; border-bottom: 1px solid #f1f5f9; }
  .stats-mini > div:nth-child(odd) { padding-right: 16px; }
  .stats-mini > div:nth-child(even) { padding-left: 16px; border-left: 1px solid #f1f5f9; }
  .stats-mini > div:nth-last-child(-n+2) { border-bottom: none; }
  .stats-mini strong { color: #334155; }
"""


def page_report():
    tl = [
        ("13:55", "green", "进入考场 · 容器就绪", "环境自检通过，初始仓库已挂载", ""),
        ("14:02", "blue", "阅读题目与 README", "打开 src/buggy_sort.py，标记 2 处可疑逻辑", ""),
        ("14:08", "amber", "运行样例测试 · 6 / 10 通过", "终端执行 pytest，记录 4 个失败用例", ""),
        ("14:15", "purple", "调用 Coding Agent · 2 轮", "引用 src/buggy_sort.py，询问并列排序问题", ""),
        ("14:22", "blue", "采纳建议 · 修改排序键", "将 amount 改为 (amount, parse_time(created_at))", ""),
        ("14:28", "green", "运行样例测试 · 8 / 10 通过", "2 个时间格式用例仍失败", ""),
        ("14:36", "amber", "第 1 次提交 · 64 分", "冻结代码与过程记录，运行隐藏测试", ""),
        ("14:58", "green", "第 2 次提交 · 82 分", "当前最高分；过程分待教师复核", "last"),
    ]
    tl_html = ""
    for t, color, title, desc, extra in tl:
        tl_html += f"""
        <div class="tl-item">
          <div class="tl-rail"><span class="tl-dot {color}"></span><span class="tl-line"></span></div>
          <div class="tl-time">{t}</div>
          <div class="tl-content"><div class="tl-title">{title}</div><div class="tl-desc">{desc}</div></div>
        </div>"""

    body = f"""
<div class="student-page">
  {student_nav("reports")}
  <div class="student-content">
    <div class="page-head">
      <div><div class="page-title">过程报告</div><div class="page-sub">软件工程 · 期中机考 · 李同学 · 学号 2023012345</div></div>
      <div class="page-actions">
        <span class="btn btn-secondary">{icon("download",14)}导出 PDF</span>
        <span class="btn btn-primary">{icon("flag",14)}发起申诉</span>
      </div>
    </div>

    <div class="report-tabs">
      <span class="tab active">总览</span>
      <span class="tab">时间线</span>
      <span class="tab">AI 对话（6）</span>
      <span class="tab">代码变更</span>
      <span class="tab">评分明细</span>
    </div>

    <div class="report-summary">
      <div class="rs-score">
        <div class="rs-label">当前总分</div>
        <div class="rs-value">82<span> / 100</span></div>
        <div class="rs-note">过程分待教师确认</div>
      </div>
      <div class="rs-item">
        <div class="rs-item-label">代码与测试</div>
        <div class="rs-item-value">66<span> / 70</span></div>
        <div class="bar"><span class="bar-fill green w-94"></span></div>
      </div>
      <div class="rs-item">
        <div class="rs-item-label">AI 协作</div>
        <div class="rs-item-value">16<span> / 20</span></div>
        <div class="bar"><span class="bar-fill purple w-80"></span></div>
      </div>
      <div class="rs-item">
        <div class="rs-item-label">教师复核</div>
        <div class="rs-item-value amber">待评<span> / 10</span></div>
        <div class="bar"><span class="bar-fill amber w-0"></span></div>
      </div>
    </div>

    <div class="report-main">
      <div class="card report-timeline-card">
        <div class="card-head">
          <div><div class="card-title">考试时间线</div><div class="card-sub">代码、测试、AI 对话与提交的关键事件</div></div>
          <span class="badge gray">18 个快照</span>
        </div>
        <div class="card-body">{tl_html}</div>
      </div>

      <div class="report-side">
        <div class="card">
          <div class="card-head"><div class="card-title">AI 协作评分</div><span class="badge purple">16 / 20</span></div>
          <div class="card-body">
            <div class="rubric-item">
              <div class="rubric-row"><span>问题拆解</span><strong>4 / 5</strong></div>
              <div class="bar"><span class="bar-fill purple w-80"></span></div>
              <div class="rubric-ev">证据：3 次任务拆解、2 次追问</div>
            </div>
            <div class="rubric-item">
              <div class="rubric-row"><span>上下文质量</span><strong>4 / 5</strong></div>
              <div class="bar"><span class="bar-fill purple w-80"></span></div>
              <div class="rubric-ev">证据：@ 引用 2 个文件，未粘贴无关代码</div>
            </div>
            <div class="rubric-item">
              <div class="rubric-row"><span>验证行为</span><strong>4 / 5</strong></div>
              <div class="bar"><span class="bar-fill purple w-80"></span></div>
              <div class="rubric-ev">证据：4 次测试运行，2 次失败后定位修正</div>
            </div>
            <div class="rubric-item last">
              <div class="rubric-row"><span>批判性采纳</span><strong>4 / 5</strong></div>
              <div class="bar"><span class="bar-fill purple w-80"></span></div>
              <div class="rubric-ev">证据：采纳 2 次，修改 1 次，拒绝 0 次</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><div class="card-title">关键统计</div><span class="link">查看明细</span></div>
          <div class="card-body stats-mini">
            <div><span>AI 对话</span><strong>6 轮</strong></div>
            <div><span>采纳建议</span><strong>2 次</strong></div>
            <div><span>测试运行</span><strong>4 次</strong></div>
            <div><span>代码快照</span><strong>18 个</strong></div>
            <div><span>代码变更</span><strong>+18 / -7</strong></div>
            <div><span>粘贴事件</span><strong>0 次</strong></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, REPORT_CSS


# ---------------------------------------------------------------------------
# 07 考试管理
# ---------------------------------------------------------------------------
EXAM_MANAGE_CSS = r"""
  .table-tools { display: flex; align-items: center; gap: 8px; }
  .table-footer .pager { display: flex; gap: 5px; }
  .page-btn { height: 23px; min-width: 23px; padding: 0 7px; border: 1px solid #e2e8f0; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 9.5px; color: #64748b; }
  .page-btn.active { background: #eff6ff; border-color: #bfdbfe; color: #1d4ed8; font-weight: 600; }
  .manage-card .table td { height: 54px; }
"""


def page_exam_manage():
    rows = """
        <tr>
          <td><div class="strong">软件工程 · 期中机考</div><div class="sub">2026 秋 · 3 道工程题</div></td>
          <td><span class="badge green">进行中</span></td>
          <td>10-25 14:00–16:00</td><td>45</td><td>38 / 90</td><td>受限</td>
          <td><a class="link" href="10-proctor.html">监考</a> <span class="muted">·</span> <span class="link">更多</span></td>
        </tr>
        <tr>
          <td><div class="strong">软件工程 · 期末机考</div><div class="sub">2026 秋 · 3 道工程题</div></td>
          <td><span class="badge gray">草稿</span></td>
          <td>11-08 09:00–11:00</td><td>45</td><td class="muted">—</td><td>受限</td>
          <td><a class="link" href="08-exam-create.html">编辑</a> <span class="muted">·</span> <span class="link">发布</span></td>
        </tr>
        <tr>
          <td><div class="strong">软件工程 · 作业 3</div><div class="sub">2026 秋 · 1 道工程题</div></td>
          <td><span class="badge gray">草稿</span></td>
          <td>11-01 19:00–20:30</td><td>45</td><td class="muted">—</td><td>受限</td>
          <td><a class="link" href="08-exam-create.html">编辑</a> <span class="muted">·</span> <span class="link">发布</span></td>
        </tr>
        <tr>
          <td><div class="strong">数据结构 · 随堂测验 3</div><div class="sub">2026 秋 · 2 道算法题</div></td>
          <td><span class="badge gray">已结束</span></td>
          <td>10-18 10:00–10:45</td><td>42</td><td>42 / 42</td><td>关闭</td>
          <td><a class="link" href="06-report.html">报告</a> <span class="muted">·</span> <span class="link">归档</span></td>
        </tr>
        <tr>
          <td><div class="strong">算法设计 · 单元测试</div><div class="sub">2026 秋 · 1 道工程题</div></td>
          <td><span class="badge gray">已结束</span></td>
          <td>10-11 14:00–15:00</td><td>38</td><td>38 / 38</td><td>开放</td>
          <td><a class="link" href="06-report.html">报告</a> <span class="muted">·</span> <span class="link">归档</span></td>
        </tr>
        <tr>
          <td><div class="strong">软件工程 · 作业 2</div><div class="sub">2026 秋 · 1 道工程题</div></td>
          <td><span class="badge gray">已结束</span></td>
          <td>09-27 19:00–20:30</td><td>45</td><td>45 / 45</td><td>受限</td>
          <td><a class="link" href="06-report.html">报告</a> <span class="muted">·</span> <span class="link">归档</span></td>
        </tr>
        <tr>
          <td><div class="strong">算法设计 · 期末机考</div><div class="sub">2026 秋 · 3 道题</div></td>
          <td><span class="badge gray">草稿</span></td>
          <td>11-15 09:00–11:00</td><td>38</td><td class="muted">—</td><td>开放</td>
          <td><a class="link" href="08-exam-create.html">编辑</a> <span class="muted">·</span> <span class="link">发布</span></td>
        </tr>"""

    body = f"""
<div class="teacher-shell">
  {teacher_sidebar("exams")}
  <div class="teacher-main">
    {teacher_topbar("考试管理", "软件工程 · 2026 秋")}
    <div class="teacher-content">
      <div class="page-head">
        <div><div class="page-title">考试管理</div><div class="page-sub">创建、发布与归档课程考试</div></div>
        <div class="page-actions">
          <span class="btn btn-secondary">{icon("users",14)}导入考生名单</span>
          <a class="btn btn-primary" href="08-exam-create.html">{icon("plus",14)}创建考试</a>
        </div>
      </div>

      <div class="stats-grid">
        {stat_card("play","green","1","进行中","1 场")}
        {stat_card("document","amber","3","待发布","草稿")}
        {stat_card("check-circle","","5","已归档","本学期")}
        {stat_card("users","purple","45","考生人数","软件工程")}
      </div>

      <div class="card manage-card">
        <div class="card-head">
          <div class="tabs">
            <span class="tab active">考试列表</span>
            <span class="tab">成绩分析</span>
            <span class="tab">归档</span>
          </div>
          <div class="table-tools">
            <span class="search-box">{icon("search",14)}搜索考试</span>
            <span class="icon-btn">{icon("filter",15)}</span>
          </div>
        </div>
        <table class="table">
          <thead><tr><th>考试名称</th><th>状态</th><th>考试时间</th><th>考生</th><th>提交</th><th>AI 模式</th><th>操作</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <div class="table-footer">
          <span>共 8 场考试 · 当前显示 7 场</span>
          <span class="pager"><span class="page-btn active">1</span><span class="page-btn">2</span><span class="page-btn">下一页</span></span>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, EXAM_MANAGE_CSS


# ---------------------------------------------------------------------------
# 08 创建考试
# ---------------------------------------------------------------------------
CREATE_CSS = r"""
  .create-main { display: flex; gap: 13px; }
  .create-form { flex: 1; min-width: 0; }
  .create-side { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .form-section { padding-bottom: 12px; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; }
  .form-section.last { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
  .section-head { display: flex; align-items: center; gap: 9px; margin-bottom: 9px; }
  .section-num { width: 22px; height: 22px; border-radius: 50%; background: #eff6ff; color: #1d4ed8; font-size: 9.5px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
  .section-title { font-size: 12px; font-weight: 700; color: #0f172a; }
  .section-sub { font-size: 9.5px; color: #94a3b8; margin-top: 1px; }
  .create-form .input, .create-form .select { height: 33px; font-size: 11px; color: #334155; }
  .create-form .field { margin-bottom: 9px; }
  .radio-row { display: flex; gap: 9px; }
  .radio-card { flex: 1; border: 1px solid #dbe2ea; border-radius: 9px; padding: 9px 10px; background: #fff; }
  .radio-card.selected { border-color: #2563eb; background: #eff6ff; }
  .rc-head { display: flex; align-items: center; justify-content: space-between; }
  .rc-title { font-size: 11px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 5px; }
  .rc-desc { font-size: 9.5px; color: #64748b; line-height: 1.5; margin-top: 4px; }
  .radio-mark { width: 14px; height: 14px; border-radius: 50%; border: 1.5px solid #cbd5e1; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .radio-card.selected .radio-mark { border-color: #2563eb; background: #2563eb; }
  .radio-dot { width: 5px; height: 5px; border-radius: 50%; background: #fff; }
  .res-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 10px; color: #64748b; }
  .res-row.last { border-bottom: none; }
  .res-row strong { color: #334155; }
  .res-note { font-size: 9px; color: #94a3b8; line-height: 1.5; margin-top: 7px; }
  .check-progress { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 9px; color: #94a3b8; }
  .check-progress .bar { flex: 1; }
  .tip-card { display: flex; gap: 9px; padding: 11px 12px; background: #eff6ff; border-color: #dbeafe; }
  .tip-icon { width: 28px; height: 28px; border-radius: 8px; background: #dbeafe; color: #1d4ed8; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .tip-title { font-size: 10.5px; font-weight: 700; color: #1e3a8a; }
  .tip-desc { font-size: 9px; color: #475569; line-height: 1.5; margin-top: 2px; }
"""


def page_exam_create():
    body = f"""
<div class="teacher-shell">
  {teacher_sidebar("exams")}
  <div class="teacher-main">
    {teacher_topbar("创建考试", "考试管理")}
    <div class="teacher-content">
      <div class="page-head">
        <div><div class="page-title">创建考试</div><div class="page-sub">配置考试时间、规则与 AI 使用策略</div></div>
        <div class="page-actions">
          <a class="btn btn-secondary" href="07-exam-manage.html">保存草稿</a>
          <a class="btn btn-primary" href="09-problem-config.html">下一步：命题{icon("arrow-right",14)}</a>
        </div>
      </div>

      <div class="create-main">
        <div class="card create-form">
          <div class="card-body">
            <div class="form-section">
              <div class="section-head"><span class="section-num">1</span><div><div class="section-title">基本信息</div><div class="section-sub">考试名称、课程与时间安排</div></div></div>
              <div class="form-grid two">
                <div class="field"><div class="label">考试名称</div><div class="input">软件工程 · 期末机考</div></div>
                <div class="field"><div class="label">课程</div><div class="select">软件工程（2026 秋）{icon("chevron-down",13,"#94a3b8")}</div></div>
              </div>
              <div class="form-grid two">
                <div class="field"><div class="label">开始时间</div><div class="input">{icon("calendar",13,"#94a3b8")}2026-11-08 09:00</div></div>
                <div class="field"><div class="label">结束时间</div><div class="input">{icon("calendar",13,"#94a3b8")}2026-11-08 11:00</div></div>
              </div>
              <div class="form-grid two">
                <div class="field"><div class="label">考试时长</div><div class="input">120 分钟</div></div>
                <div class="field"><div class="label">及格线</div><div class="input">60 分</div></div>
              </div>
            </div>

            <div class="form-section">
              <div class="section-head"><span class="section-num">2</span><div><div class="section-title">考试规则</div><div class="section-sub">提交次数与成绩计算</div></div></div>
              <div class="form-grid two">
                <div class="field"><div class="label">提交次数上限</div><div class="input">2 次</div></div>
                <div class="field"><div class="label">成绩计算</div><div class="select">取最高分{icon("chevron-down",13,"#94a3b8")}</div></div>
              </div>
              <div class="form-grid two">
                <div class="field"><div class="label">迟到入场</div><div class="select">开考 15 分钟后禁止入场{icon("chevron-down",13,"#94a3b8")}</div></div>
                <div class="field"><div class="label">交卷规则</div><div class="select">时间到自动交卷{icon("chevron-down",13,"#94a3b8")}</div></div>
              </div>
            </div>

            <div class="form-section">
              <div class="section-head"><span class="section-num">3</span><div><div class="section-title">AI 使用策略</div><div class="section-sub">决定考生可以使用 Coding Agent 的范围</div></div></div>
              <div class="radio-row">
                <div class="radio-card">
                  <div class="rc-head"><div class="rc-title">{icon("unlock",13,"#64748b")}开放</div><div class="radio-mark"></div></div>
                  <div class="rc-desc">完整对话与代码修改，全部留痕。</div>
                </div>
                <div class="radio-card selected">
                  <div class="rc-head"><div class="rc-title">{icon("shield",13,"#1d4ed8")}受限</div><div class="radio-mark"><span class="radio-dot"></span></div></div>
                  <div class="rc-desc">仅解释与运行测试，不可直接写入代码。</div>
                </div>
                <div class="radio-card">
                  <div class="rc-head"><div class="rc-title">{icon("lock",13,"#64748b")}关闭</div><div class="radio-mark"></div></div>
                  <div class="rc-desc">禁用 Agent，入口不可用。</div>
                </div>
              </div>
            </div>

            <div class="form-section last">
              <div class="section-head"><span class="section-num">4</span><div><div class="section-title">资源与网络</div><div class="section-sub">每位考生独立容器</div></div></div>
              <div class="form-grid four">
                <div class="field"><div class="label">CPU</div><div class="input">2 vCPU</div></div>
                <div class="field"><div class="label">内存</div><div class="input">4 GB</div></div>
                <div class="field"><div class="label">网络</div><div class="select">仅平台网关{icon("chevron-down",12,"#94a3b8")}</div></div>
                <div class="field"><div class="label">镜像</div><div class="select">se-2026-python{icon("chevron-down",12,"#94a3b8")}</div></div>
              </div>
            </div>
          </div>
        </div>

        <div class="create-side">
          <div class="card">
            <div class="card-head"><div class="card-title">发布前检查</div><span class="badge amber">4 / 5</span></div>
            <div class="card-body">
              {check_line("考试时间已设置")}
              {check_line("考生名单已导入（45 人）")}
              {check_line("镜像可用")}
              {check_line("题目与测试待配置（0 / 3）", ok=False)}
              {check_line("AI 策略已选择（受限）")}
              <div class="check-progress"><div class="bar"><span class="bar-fill amber w-80"></span></div><span>4 / 5 完成</span></div>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><div class="card-title">资源预估</div></div>
            <div class="card-body">
              <div class="res-row"><span>考生人数</span><strong>45 人</strong></div>
              <div class="res-row"><span>容器数量</span><strong>45 个</strong></div>
              <div class="res-row"><span>CPU</span><strong>90 vCPU</strong></div>
              <div class="res-row last"><span>内存</span><strong>180 GB</strong></div>
              <div class="res-note">按每位考生 2 vCPU / 4 GB 估算，考试期间按需启动。</div>
            </div>
          </div>

          <div class="card tip-card">
            <div class="tip-icon">{icon("sparkles",15)}</div>
            <div><div class="tip-title">发布后可撤回</div><div class="tip-desc">考试开始前仍可撤回并修改配置；开始后配置冻结。</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, CREATE_CSS


# ---------------------------------------------------------------------------
# 09 命题与评测配置
# ---------------------------------------------------------------------------
PROBLEM_CSS = r"""
  .problem-summary { display: flex; align-items: center; justify-content: space-between; padding: 13px 16px; margin-bottom: 13px; }
  .ps-main { display: flex; align-items: center; gap: 12px; }
  .ps-icon { width: 38px; height: 38px; border-radius: 10px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .ps-title { font-size: 12.5px; font-weight: 700; color: #0f172a; }
  .ps-meta { display: flex; align-items: center; gap: 7px; margin-top: 5px; }
  .ps-file { display: flex; align-items: center; gap: 4px; font-size: 9.5px; color: #94a3b8; margin-left: 4px; }
  .problem-main { display: flex; gap: 13px; }
  .test-card { flex: 1; min-width: 0; }
  .problem-side { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .test-tabs { display: flex; gap: 22px; padding: 0 16px; border-bottom: 1px solid #eef2f7; }
  .test-tabs .tab { height: 35px; }
  .test-card .table td { height: 45px; }
  .test-card .table th { height: 34px; }
  .res-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 10px; color: #64748b; }
  .res-row.last { border-bottom: none; }
  .res-row strong { color: #334155; }
  .weight-row { display: flex; justify-content: space-between; font-size: 10px; color: #475569; margin: 8px 0 4px; }
  .weight-row strong { color: #334155; }
  .weight-note { font-size: 9px; color: #94a3b8; line-height: 1.5; margin-top: 9px; }
  .tip-card.amber { background: #fffbeb; border-color: #fde68a; }
  .tip-icon.amber { background: #fef3c7; color: #d97706; }
  .tip-title.amber { color: #92400e; }
  .tip-desc.amber { color: #78350f; }
"""


def page_problem_config():
    rows = """
        <tr><td>#01</td><td>test_sort_basic</td><td>样例</td><td><span class="badge green">通过</span></td><td>0.12s</td><td>12 MB</td><td>可见</td></tr>
        <tr><td>#02</td><td>test_sort_ties</td><td>样例</td><td><span class="badge green">通过</span></td><td>0.10s</td><td>11 MB</td><td>可见</td></tr>
        <tr><td>#03</td><td>test_sort_iso</td><td>样例</td><td><span class="badge green">通过</span></td><td>0.11s</td><td>12 MB</td><td>可见</td></tr>
        <tr><td>#04</td><td>case_04</td><td>隐藏</td><td><span class="badge green">通过</span></td><td>0.18s</td><td>16 MB</td><td>不可见</td></tr>
        <tr><td>#05</td><td>case_05</td><td>隐藏</td><td><span class="badge red">失败</span></td><td>0.20s</td><td>18 MB</td><td>不可见</td></tr>
        <tr><td>#06</td><td>case_06</td><td>隐藏</td><td><span class="badge green">通过</span></td><td>0.17s</td><td>15 MB</td><td>不可见</td></tr>"""

    body = f"""
<div class="teacher-shell">
  {teacher_sidebar("exams")}
  <div class="teacher-main">
    {teacher_topbar("命题与评测配置", "考试管理")}
    <div class="teacher-content">
      <div class="page-head">
        <div><div class="page-title">命题与评测配置</div><div class="page-sub">软件工程 · 期末机考 · 任务 1 / 3</div></div>
        <div class="page-actions">
          <span class="btn btn-secondary">{icon("eye",14)}预览题面</span>
          <a class="btn btn-primary" href="07-exam-manage.html">{icon("check",14)}保存任务</a>
        </div>
      </div>

      <div class="card problem-summary">
        <div class="ps-main">
          <div class="ps-icon">{icon("document",19)}</div>
          <div>
            <div class="ps-title">任务 1：修复订单排序并补充测试</div>
            <div class="ps-meta">
              <span class="badge blue">工程题</span>
              <span class="badge gray">Python 3.11</span>
              <span class="badge green">题面已保存</span>
              <span class="ps-file">{icon("file",11)}exam-project.zip</span>
            </div>
          </div>
        </div>
        <span class="btn btn-ghost btn-sm">编辑题面</span>
      </div>

      <div class="problem-main">
        <div class="card test-card">
          <div class="card-head">
            <div><div class="card-title">测试用例</div><div class="card-sub">样例测试对考生可见；隐藏测试仅用于判分</div></div>
            <div class="table-tools">
              <span class="btn btn-secondary btn-sm">{icon("plus",12)}上传用例</span>
              <span class="btn btn-secondary btn-sm">{icon("play",12)}运行全部</span>
            </div>
          </div>
          <div class="test-tabs"><span class="tab active">样例测试 <span class="tab-count">10</span></span><span class="tab">隐藏测试 <span class="tab-count">8</span></span></div>
          <table class="table">
            <thead><tr><th>编号</th><th>名称</th><th>类型</th><th>状态</th><th>耗时</th><th>内存</th><th>可见性</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
          <div class="table-footer"><span>共 18 个用例 · 当前显示 6 个</span><span class="link">批量导入 CSV</span></div>
        </div>

        <div class="problem-side">
          <div class="card">
            <div class="card-head"><div class="card-title">评分规则</div><span class="badge blue">总分 100</span></div>
            <div class="card-body">
              <div class="weight-row"><span>必过用例</span><strong>60%</strong></div>
              <div class="bar"><span class="bar-fill w-60"></span></div>
              <div class="weight-row"><span>加分用例</span><strong>30%</strong></div>
              <div class="bar"><span class="bar-fill green w-30"></span></div>
              <div class="weight-row"><span>代码质量</span><strong>10%</strong></div>
              <div class="bar"><span class="bar-fill amber w-10"></span></div>
              <div class="weight-note">必过用例全部通过才可获得加分用例分数；未通过则最高 60 分。</div>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><div class="card-title">运行限制</div></div>
            <div class="card-body">
              <div class="res-row"><span>单用例超时</span><strong>2.0 s</strong></div>
              <div class="res-row"><span>内存上限</span><strong>256 MB</strong></div>
              <div class="res-row"><span>判题语言</span><strong>Python 3.11</strong></div>
              <div class="res-row last"><span>AI 策略</span><strong>继承考试：受限</strong></div>
            </div>
          </div>

          <div class="card tip-card amber">
            <div class="tip-icon amber">{icon("alert",14)}</div>
            <div><div class="tip-title amber">隐藏测试不可泄露</div><div class="tip-desc amber">隐藏用例不会挂载到考生容器，仅在独立判题沙箱中运行。</div></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, PROBLEM_CSS


# ---------------------------------------------------------------------------
# 10 监考中心
# ---------------------------------------------------------------------------
PROCTOR_CSS = r"""
  .proctor-main { display: flex; gap: 13px; }
  .candidate-card { flex: 1; min-width: 0; }
  .alert-side { width: 360px; flex-shrink: 0; display: flex; flex-direction: column; gap: 13px; }
  .candidate-card .table td { height: 50px; }
  .candidate-name { display: flex; align-items: center; gap: 8px; }
  .mini-avatar { width: 26px; height: 26px; border-radius: 50%; background: #e0e7ff; color: #3730a3; display: flex; align-items: center; justify-content: center; font-size: 9.5px; font-weight: 700; flex-shrink: 0; }
  .candidate-sub { font-size: 9px; color: #94a3b8; margin-top: 1px; }
  .alert-item { border: 1px solid #eef2f7; border-radius: 8px; padding: 9px 10px; margin-bottom: 8px; }
  .alert-item.last { margin-bottom: 0; }
  .alert-item.high { border-color: #fecaca; background: #fef2f2; }
  .alert-item.medium { border-color: #fde68a; background: #fffbeb; }
  .alert-item.low { border-color: #e2e8f0; background: #f8fafc; }
  .alert-top { display: flex; align-items: center; justify-content: space-between; }
  .alert-time { font-size: 9px; color: #94a3b8; }
  .alert-title { font-size: 10.5px; font-weight: 700; color: #334155; margin-top: 5px; }
  .alert-desc { font-size: 9px; color: #64748b; line-height: 1.5; margin-top: 2px; }
  .alert-actions { display: flex; gap: 6px; margin-top: 7px; }
  .log-item { display: flex; gap: 8px; padding: 5px 0; border-bottom: 1px solid #f1f5f9; }
  .log-item.last { border-bottom: none; }
  .log-dot { width: 6px; height: 6px; border-radius: 50%; background: #cbd5e1; margin-top: 5px; flex-shrink: 0; }
  .log-text { font-size: 10px; color: #475569; }
  .log-sub { font-size: 9px; color: #94a3b8; margin-top: 1px; }
"""


def page_proctor():
    candidates = [
        ("李", "李同学", "2023012345", '<span class="badge blue">作答中</span>', "任务 1 / 3", "1", "6 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
        ("王", "王同学", "2023012388", '<span class="badge blue">作答中</span>', "任务 1 / 3", "0", "2 轮", '<span class="badge red">高 1</span>', '<span class="link">处置</span>'),
        ("陈", "陈同学", "2023012301", '<span class="badge green">已提交</span>', "3 / 3", "2", "12 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
        ("赵", "赵同学", "2023012322", '<span class="badge amber">断线重连</span>', "任务 2 / 3", "1", "4 轮", '<span class="badge amber">低 1</span>', '<span class="link">处置</span>'),
        ("孙", "孙同学", "2023012340", '<span class="badge blue">作答中</span>', "任务 1 / 3", "0", "0 轮", '<span class="badge amber">中 1</span>', '<span class="link">处置</span>'),
        ("周", "周同学", "2023012356", '<span class="badge blue">作答中</span>', "任务 2 / 3", "1", "8 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
        ("吴", "吴同学", "2023012367", '<span class="badge blue">作答中</span>', "任务 1 / 3", "0", "3 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
        ("郑", "郑同学", "2023012379", '<span class="badge green">已提交</span>', "3 / 3", "2", "10 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
        ("冯", "冯同学", "2023012384", '<span class="badge blue">作答中</span>', "任务 2 / 3", "1", "5 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
        ("褚", "褚同学", "2023012391", '<span class="badge blue">作答中</span>', "任务 1 / 3", "0", "1 轮", '<span class="muted">—</span>', '<a class="link" href="06-report.html">查看</a>'),
    ]
    rows = ""
    for initial, name, sid, status, progress, submits, rounds, alerts, action in candidates:
        rows += f"""
        <tr>
          <td><div class="candidate-name"><div class="mini-avatar">{initial}</div><div><div class="strong">{name}</div><div class="candidate-sub">{sid}</div></div></div></td>
          <td>{status}</td><td>{progress}</td><td>{submits}</td><td>{rounds}</td><td>{alerts}</td><td>{action}</td>
        </tr>"""

    body = f"""
<div class="teacher-shell">
  {teacher_sidebar("proctor")}
  <div class="teacher-main">
    {teacher_topbar("监考中心", "考试管理")}
    <div class="teacher-content">
      <div class="page-head">
        <div><div class="page-title">监考中心</div><div class="page-sub">软件工程 · 期中机考 · 进行中 · 14:32:26</div></div>
        <div class="page-actions">
          <span class="btn btn-secondary">{icon("download",14)}导出异常记录</span>
          <a class="btn btn-danger" href="07-exam-manage.html">结束考试</a>
        </div>
      </div>

      <div class="stats-grid">
        {stat_card("users","green","42 / 45","在线考生","")}
        {stat_card("check-circle","","38","已提交","")}
        {stat_card("alert","red","3","异常告警","1 高 · 1 中 · 1 低","red")}
        {stat_card("clock","amber","01:27:34","剩余时间","")}
      </div>

      <div class="proctor-main">
        <div class="card candidate-card">
          <div class="card-head">
            <div><div class="card-title">考生状态</div><div class="card-sub">按告警级别与进度排序</div></div>
            <div class="table-tools">
              <span class="search-box">{icon("search",13)}搜索考生</span>
              <span class="btn btn-secondary btn-sm">{icon("filter",12)}筛选</span>
            </div>
          </div>
          <table class="table">
            <thead><tr><th>考生</th><th>状态</th><th>进度</th><th>提交</th><th>AI 对话</th><th>告警</th><th>操作</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
          <div class="table-footer"><span>在线 42 / 45 · 最近更新 14:32:26</span><span class="link">查看全部考生</span></div>
        </div>

        <div class="alert-side">
          <div class="card">
            <div class="card-head"><div class="card-title">异常告警</div><span class="badge red">1 高 · 1 中 · 1 低</span></div>
            <div class="card-body">
              <div class="alert-item high">
                <div class="alert-top"><span class="badge red">高</span><span class="alert-time">14:41:08</span></div>
                <div class="alert-title">王同学 · 粘贴大段代码</div>
                <div class="alert-desc">检测到 120 行剪贴板内容，已生成代码快照 #17。</div>
                <div class="alert-actions"><span class="btn btn-secondary btn-sm">查看证据</span><span class="btn btn-danger btn-sm">终止考试</span></div>
              </div>
              <div class="alert-item medium">
                <div class="alert-top"><span class="badge amber">中</span><span class="alert-time">14:36:20</span></div>
                <div class="alert-title">赵同学 · 网络中断 42s</div>
                <div class="alert-desc">已自动重连并恢复到快照 #14；可考虑补时。</div>
                <div class="alert-actions"><span class="btn btn-secondary btn-sm">补时 2 分钟</span><span class="btn btn-secondary btn-sm">查看</span></div>
              </div>
              <div class="alert-item low last">
                <div class="alert-top"><span class="badge gray">低</span><span class="alert-time">14:28:05</span></div>
                <div class="alert-title">孙同学 · 窗口切换 3 次</div>
                <div class="alert-desc">切出考试页面 3 次，每次不足 5 秒；暂无外部模型调用。</div>
                <div class="alert-actions"><span class="btn btn-secondary btn-sm">忽略</span><span class="btn btn-secondary btn-sm">查看</span></div>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-head"><div class="card-title">处置记录</div><span class="link">查看全部</span></div>
            <div class="card-body">
              <div class="log-item"><span class="log-dot"></span><div><div class="log-text">14:36 为赵同学补时 2 分钟</div><div class="log-sub">理由：网络中断 42 秒 · 助教 张</div></div></div>
              <div class="log-item"><span class="log-dot"></span><div><div class="log-text">14:30 警告王同学：请勿粘贴外部代码</div><div class="log-sub">处置人：监考 刘</div></div></div>
              <div class="log-item last"><span class="log-dot"></span><div><div class="log-text">14:10 重新分配容器给陈同学</div><div class="log-sub">原因：容器启动超时 · 自动恢复</div></div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>"""
    return body, PROCTOR_CSS


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------
INDEX_CSS = r"""
  .index-page { background: #f5f7fb; padding: 34px 40px; display: flex; flex-direction: column; }
  .index-head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 20px; }
  .index-title { font-size: 24px; font-weight: 700; color: #0f172a; margin-top: 10px; }
  .index-sub { font-size: 11.5px; color: #64748b; margin-top: 4px; }
  .index-note { font-size: 10.5px; color: #94a3b8; }
  .index-grid { display: flex; flex-wrap: wrap; gap: 12px; }
  .index-card { width: 665px; height: 112px; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px 17px; display: flex; align-items: flex-start; gap: 13px; }
  .idx-num { width: 34px; height: 34px; border-radius: 9px; background: #eff6ff; color: #1d4ed8; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
  .idx-title { font-size: 13px; font-weight: 700; color: #0f172a; }
  .idx-desc { font-size: 10.5px; color: #64748b; margin-top: 4px; line-height: 1.5; }
  .idx-role { margin-left: auto; }
  .index-foot { margin-top: auto; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; }
"""


def page_index():
    pages = [
        ("01", "登录与角色入口", "三种登录态：点角色切换，点登录进入对应端。", "公共", "01-login.html"),
        ("02", "考试列表与详情", "待考考试高亮、考试列表、考试须知与设备检查。", "考生", "02-exam-list.html"),
        ("03", "环境自检", "阅读须知后的六项自检、考试信息与进入考场。", "考生", "03-precheck.html"),
        ("04", "答题工作台", "三栏 IDE + 终端 + Coding Agent，含受限模式与留痕。", "考生", "04-workbench.html"),
        ("05", "提交与判分结果", "总分、样例/隐藏用例结果、提交记录与剩余次数。", "考生", "05-result.html"),
        ("06", "过程报告", "考试时间线、AI 协作评分、关键统计与申诉入口。", "考生", "06-report.html"),
        ("07", "考试管理", "考试列表、状态、AI 模式、成绩分析 tab 与创建入口。", "教师", "07-exam-manage.html"),
        ("08", "创建考试", "时间、规则、AI 策略、资源网络与发布前检查。", "教师", "08-exam-create.html"),
        ("09", "命题与评测配置", "题面仓库、样例/隐藏测试、评分权重与运行限制。", "教师", "09-problem-config.html"),
        ("10", "监考中心", "考生状态、三级告警、处置动作与处置记录。", "教师 / 助教", "10-proctor.html"),
    ]
    cards = ""
    for num, title, desc, role, href in pages:
        cards += f"""
    <a class="index-card" href="{href}">
      <span class="idx-num">{num}</span>
      <div><div class="idx-title">{title}</div><div class="idx-desc">{desc}</div></div>
      <span class="idx-role badge gray">{role}</span>
    </a>"""
    body = f"""
<div class="index-page">
  <div class="index-head">
    <div>
      <div class="brand"><div class="logo">{icon("logo",17,"#ffffff",2.2)}</div><div class="brand-name">AI Coding 考试平台</div></div>
      <div class="index-title">产品原型 · 核心 10 页</div>
      <div class="index-sub">全浅色 SaaS · 1440×900 · 可直接点击浏览本地 HTML</div>
    </div>
    <div class="index-note">建议导入墨刀时按 01 → 10 的顺序导入，再按 README 的热区表连线。</div>
  </div>
  <div class="index-grid">{cards}</div>
  <div class="index-foot">考生主路径：01 登录 → 02 考试列表 → 03 环境自检 → 04 工作台 → 05 提交结果 → 06 过程报告；教师主路径：01 登录 → 07 考试管理 → 08 创建考试 → 09 命题配置 → 10 监考中心。</div>
</div>"""
    return body, INDEX_CSS


PAGES = [
    ("01-login.html", "登录 · AI Coding 考试平台", lambda: page_login("student")),
    ("01-login-teacher.html", "教师登录 · AI Coding 考试平台", lambda: page_login("teacher")),
    ("01-login-admin.html", "管理员登录 · AI Coding 考试平台", lambda: page_login("admin")),
    ("02-exam-list.html", "我的考试 · AI Coding 考试平台", page_exam_list),
    ("03-precheck.html", "进入考场 · AI Coding 考试平台", page_precheck),
    ("05-result.html", "提交结果 · AI Coding 考试平台", page_result),
    ("06-report.html", "过程报告 · AI Coding 考试平台", page_report),
    ("07-exam-manage.html", "考试管理 · AI Coding 考试平台", page_exam_manage),
    ("08-exam-create.html", "创建考试 · AI Coding 考试平台", page_exam_create),
    ("09-problem-config.html", "命题与评测配置 · AI Coding 考试平台", page_problem_config),
    ("10-proctor.html", "监考中心 · AI Coding 考试平台", page_proctor),
    ("index.html", "原型页面导航 · AI Coding 考试平台", page_index),
]


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for filename, title, fn in PAGES:
        body, css = fn()
        (OUT_DIR / filename).write_text(doc(title, body, css), encoding="utf-8")
        print(f"generated 本地预览版/{filename}")


if __name__ == "__main__":
    main()

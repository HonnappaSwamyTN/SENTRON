"""Generate clean, high-resolution architectural diagrams for SENTRON V1 report."""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Directory for diagrams
OUT_DIR = Path(__file__).resolve().parent / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Color Palette (Dark Professional Engineering Theme)
BG_COLOR = (15, 23, 42)         # #0f172a slate-900
CARD_BG = (30, 41, 59)          # #1e293b slate-800
CARD_BORDER = (51, 65, 85)      # #334155 slate-700
HEADER_BG = (30, 58, 138)       # #1e3a8a blue-900
ACCENT_BLUE = (37, 99, 235)     # #2563eb blue-600
ACCENT_CYAN = (6, 182, 212)     # #06b6d4 cyan-500
ACCENT_GREEN = (22, 163, 74)    # #16a34a green-600
ACCENT_AMBER = (217, 119, 6)    # #d97706 amber-600
ACCENT_RED = (220, 38, 38)      # #dc2626 red-600
TEXT_WHITE = (248, 250, 252)    # #f8fafc slate-50
TEXT_MUTED = (148, 163, 184)    # #94a3b8 slate-400
TEXT_DARK = (15, 23, 42)
LINE_COLOR = (100, 116, 139)    # #64748b slate-500

def get_font(size: int, bold: bool = False, mono: bool = False):
    font_dir = "C:/Windows/Fonts"
    if mono:
        name = "consola.ttf"
    elif bold:
        name = "segoeuib.ttf" if os.path.exists(os.path.join(font_dir, "segoeuib.ttf")) else "arialbd.ttf"
    else:
        name = "segoeui.ttf" if os.path.exists(os.path.join(font_dir, "segoeui.ttf")) else "arial.ttf"
    path = os.path.join(font_dir, name)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_rounded_card(draw, box, fill, border, radius=10, border_width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=border, width=border_width)

def draw_arrow(draw, start, end, color=ACCENT_CYAN, width=3, arrow_size=8):
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - arrow_size * math.cos(angle - math.pi / 6), y2 - arrow_size * math.sin(angle - math.pi / 6))
    p2 = (x2 - arrow_size * math.cos(angle + math.pi / 6), y2 - arrow_size * math.sin(angle + math.pi / 6))
    draw.polygon([end, p1, p2], fill=color)

# -------------------------------------------------------------
# 1. OVERALL SYSTEM ARCHITECTURE DIAGRAM
# -------------------------------------------------------------
def generate_system_architecture():
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    f_title = get_font(26, bold=True)
    f_sub = get_font(15, bold=False)
    f_box_title = get_font(18, bold=True)
    f_box_sub = get_font(13, bold=False)
    f_item = get_font(13, bold=False)
    f_badge = get_font(11, bold=True)

    # Title header banner
    draw.text((50, 30), "SENTRON V1 — Overall System Architecture", fill=TEXT_WHITE, font=f_title)
    draw.text((50, 68), "Local-First Desktop Protection Suite • PySide6 Desktop Hub • Deterministic AgentGuard • Genuine CrashGuard Telemetry", fill=TEXT_MUTED, font=f_sub)
    draw.line([(50, 95), (1550, 95)], fill=CARD_BORDER, width=2)

    # UI Layer (Top)
    draw_rounded_card(draw, (50, 115, 1550, 245), CARD_BG, (37, 99, 235), radius=12, border_width=2)
    draw.text((70, 128), "DESKTOP UI LAYER (PySide6 / Qt 6)", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((450, 132), "Runs on main Qt GUI thread • Non-blocking signals • Freely resizable (min 880x540)", fill=TEXT_MUTED, font=f_sub)

    # UI Components
    ui_boxes = [
        (70, 160, 400, 230, "Movable Floating Hub", "Always-on-top, draggable\nLive module status & badges", ACCENT_BLUE),
        (420, 160, 750, 230, "Live Security & Health Dashboard", "AgentGuard scenario inspector\nCrashGuard QPainter trend chart", (16, 185, 129)),
        (770, 160, 1130, 230, "Unified Timeline & Search", "Interleaved audit & health events\nCausality disclaimer banner", (245, 158, 11)),
        (1150, 160, 1530, 230, "CrashGuard Alert Popup", "Non-modal, non-focus-stealing\nSimulated badge, View Details / Dismiss", (239, 68, 68)),
    ]
    for bx1, by1, bx2, by2, title, desc, col in ui_boxes:
        draw_rounded_card(draw, (bx1, by1, bx2, by2), (20, 30, 48), col, radius=8, border_width=1)
        draw.text((bx1 + 12, by1 + 10), title, fill=TEXT_WHITE, font=get_font(14, bold=True))
        y_d = by1 + 32
        for line in desc.split("\n"):
            draw.text((bx1 + 12, y_d), line, fill=TEXT_MUTED, font=get_font(11))
            y_d += 16

    # Signal Bridge Layer
    draw.line([(800, 245), (800, 280)], fill=ACCENT_CYAN, width=3)
    draw.text((815, 255), "Qt Signals / Thread-Safe Invocations (snapshot_received, alert_received, event_recorded)", fill=ACCENT_CYAN, font=get_font(12, bold=True))

    # Core Subsystems Container
    # Left: AgentGuard
    draw_rounded_card(draw, (50, 290, 780, 800), CARD_BG, (59, 130, 246), radius=12, border_width=2)
    draw.text((70, 305), "AGENTGUARD SUBSYSTEM (AI-Agent Governance)", fill=ACCENT_BLUE, font=f_box_title)
    draw.text((70, 332), "Deterministic Action Interception, Policy Evaluation & Execution Gating", fill=TEXT_MUTED, font=f_sub)

    ag_modules = [
        ("A. Suspicious-Input Analyzer", "Regex pattern matching for prompt injection overrides, jailbreaks, and delimiter breakouts.\nEmits advisory RiskSignal objects. Never independently authorizes actions.", (14, 165, 233)),
        ("B. Sensitive-Data Detector", "Scans payloads for API keys (sk-, ghp-, AKIA-), tokens, and passwords.\nSanitizes cleartext before SQLite persistence with [REDACTED_*]. Explicit pattern limits.", (168, 85, 247)),
        ("C. Deterministic Policy Engine", "Evaluates ActionRequest -> ALLOW / ASK / BLOCK. Priority: BLOCK > ASK > ALLOW.\nDefaults to ASK (fail-closed). Always blocks prohibited ops. Scoped narrow allow rules.", (234, 179, 8)),
        ("D. Scoped Approval Manager", "Enforces fine-grained approval bounds (agent, op, target, destination, session, expiry).\nDefault 300s TTL, single-use. Any scope parameter change invalidates prior approval.", (249, 115, 22)),
        ("E. Controlled Execution Gatekeeper", "Sole authorized execution boundary. Blocked & unapproved actions never reach handler.\nV1 safe mock executor simulates tools. Arbitrary shell & destructive operations prohibited.", (34, 197, 94)),
        ("F. Security Audit Logger", "SqliteAuditLog writes redacted audit records to local SQLite events table.\nPowers latest 5 security events feed and keyword/agent/severity search.", (100, 116, 139)),
    ]
    y_m = 360
    for title, desc, col in ag_modules:
        draw_rounded_card(draw, (70, y_m, 760, y_m + 65), (20, 30, 48), col, radius=6, border_width=1)
        draw.text((82, y_m + 6), title, fill=TEXT_WHITE, font=get_font(13, bold=True))
        y_sub = y_m + 25
        for line in desc.split("\n"):
            draw.text((82, y_sub), line, fill=TEXT_MUTED, font=get_font(11))
            y_sub += 15
        y_m += 72

    # Right: CrashGuard
    draw_rounded_card(draw, (820, 290, 1550, 800), CARD_BG, (16, 185, 129), radius=12, border_width=2)
    draw.text((840, 305), "CRASHGUARD SUBSYSTEM (OS Health & Recovery)", fill=(16, 185, 129), font=f_box_title)
    draw.text((840, 332), "Passive Telemetry Monitoring, Sustained-Risk Alerts & Safe Recovery Guidance", fill=TEXT_MUTED, font=f_sub)

    cg_modules = [
        ("A. Metrics Collector (psutil)", "Gathers genuine CPU %, virtual memory %, disk free GB, and top 5 processes by memory.\nExplicitly reports unavailable counters in unavailable_metrics. Zero fabricated data.", (34, 197, 94)),
        ("B. Background Monitoring Worker", "Dedicated background thread (interval 2-10s). Maintains bounded ring buffer (60 samples).\nClean shutdown within 2 seconds. Severe load backoff suppresses secondary scans.", (14, 165, 233)),
        ("C. Sustained-Risk Detector", "Evaluates telemetry against sustained thresholds (CPU 85%, RAM 85%, Disk 5GB).\nFilters transient spikes. Enforces duration window & cooldown. Spike != crash.", (234, 179, 8)),
        ("D. Windows Evidence Collector", "Queries Windows Application event logs for Event IDs 1000 (Crash) and 1002 (Hang).\nStrictly separates confirmed observations from suspected hypotheses. Graceful fallback.", (168, 85, 247)),
        ("E. Safe Recovery Advisor", "Advises user interventions: save open work, close idle heavy processes, check loops.\nStrictly non-destructive: NEVER automatically terminates, suspends, or kills processes.", (239, 68, 68)),
        ("F. Simulation & Verification Support", "Explicit synthetic high-load triggers for demo verification. Labels alerts [SIMULATED DEMO ALERT].\nQuick reset clears synthetic risk states while authentic monitoring continues.", (100, 116, 139)),
    ]
    y_m = 360
    for title, desc, col in cg_modules:
        draw_rounded_card(draw, (840, y_m, 1530, y_m + 65), (20, 30, 48), col, radius=6, border_width=1)
        draw.text((852, y_m + 6), title, fill=TEXT_WHITE, font=get_font(13, bold=True))
        y_sub = y_m + 25
        for line in desc.split("\n"):
            draw.text((852, y_sub), line, fill=TEXT_MUTED, font=get_font(11))
            y_sub += 15
        y_m += 72

    # Bottom Layer: Shared Core & Storage + Platform
    draw_rounded_card(draw, (50, 820, 1020, 960), CARD_BG, (245, 158, 11), radius=10, border_width=2)
    draw.text((70, 832), "SHARED CORE & LOCAL SQLITE EVENT STORE (sentron.core)", fill=(245, 158, 11), font=f_box_title)
    draw.text((70, 860), "Local ACID persistence in 'sentron_local.db' (or in-memory for testing). Schema table 'events' (event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted). Indexes on timestamp, subsystem, event_type. Configurable retention purging (purge_older_than). Strict redaction of secrets before persistence.", fill=TEXT_MUTED, font=f_item)
    draw.text((70, 920), "Core Models: ActionRequest, PolicyResult, ApprovalScope, AuditEvent, ExecutionResult, RiskSignal, SystemSnapshot, RiskAlert, WindowsEvidence, RecoveryRecommendation, UnifiedEvent.", fill=(203, 213, 225), font=get_font(12, mono=True))

    draw_rounded_card(draw, (1050, 820, 1550, 960), CARD_BG, (148, 163, 184), radius=10, border_width=2)
    draw.text((1070, 832), "PLATFORM ADAPTERS & ISOLATION (Windows-First)", fill=TEXT_WHITE, font=f_box_title)
    draw.text((1070, 860), "Windows Event Log Query Adapter via PowerShell Get-WinEvent (timeout & access-denied handling).\nHandles unprivileged execution gracefully; logs access denial in unavailable_metrics.\nZero Cloud SDKs: 0 imports of openai, anthropic, or cloud endpoints. 100% offline local-first.", fill=TEXT_MUTED, font=f_item)
    draw.text((1070, 920), "Target OS: Windows 10/11 Workstations • Python 3.11+ • PySide6 • psutil", fill=ACCENT_CYAN, font=get_font(12, bold=True))

    out_file = OUT_DIR / "diagram_system_architecture.png"
    img.save(out_file)
    print(f"Saved: {out_file}")

# -------------------------------------------------------------
# 2. AGENTGUARD DETAILED WORKFLOW FLOWCHART
# -------------------------------------------------------------
def generate_agentguard_workflow():
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    f_title = get_font(26, bold=True)
    f_sub = get_font(15, bold=False)
    f_box_title = get_font(15, bold=True)
    f_box_desc = get_font(12, bold=False)

    draw.text((50, 30), "AgentGuard — End-to-End Governance & Controlled Execution Workflow", fill=TEXT_WHITE, font=f_title)
    draw.text((50, 68), "Structured Action Request -> Rule Analysis -> Policy Gating -> Human Approval -> Controlled Execution -> Redacted Audit", fill=TEXT_MUTED, font=f_sub)
    draw.line([(50, 95), (1550, 95)], fill=CARD_BORDER, width=2)

    # Step 1: Agent Request
    draw_rounded_card(draw, (50, 130, 270, 250), (30, 41, 59), ACCENT_BLUE, radius=8)
    draw.text((65, 145), "1. AI AGENT TOOL CALL", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((65, 175), "Proposes ActionRequest:\n• agent_id & tool_name\n• operation & target\n• data_classification\n• untrusted_text payload\n• session_id & timestamp", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (270, 190), (330, 190))

    # Step 2: Parallel Analysis (Input Risk & Sensitive Data)
    draw_rounded_card(draw, (330, 120, 620, 260), (30, 41, 59), (168, 85, 247), radius=8)
    draw.text((345, 135), "2. DETERMINISTIC ANALYZERS", fill=(168, 85, 247), font=f_box_title)
    draw.text((345, 162), "Suspicious-Input Analyzer:\n• Prompt injection override signatures\n• Jailbreak / roleplay markers\n• Emits advisory RiskSignals (low/high/crit)\nSensitive-Data Detector:\n• Scans API keys, tokens, passwords\n• Flags secret presence & redacts text", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (620, 190), (680, 190))

    # Step 3: Deterministic Policy Engine
    draw_rounded_card(draw, (680, 120, 960, 260), (30, 41, 59), (234, 179, 8), radius=8)
    draw.text((695, 135), "3. POLICY ENGINE EVALUATION", fill=(234, 179, 8), font=f_box_title)
    draw.text((695, 162), "Matches rules: BLOCK > ASK > ALLOW\n• Always block: prohibited ops list\n• Risk flags or secrets? -> Force ASK\n• Explicit narrow allow rule? -> ALLOW\n• Unknown / malformed? -> Default ASK\nOutputs authoritative PolicyResult", fill=TEXT_MUTED, font=f_box_desc)

    # Decision branches from Policy Engine
    # Branch A: BLOCK (Top Right)
    draw_arrow(draw, (960, 150), (1030, 150), color=ACCENT_RED)
    draw_rounded_card(draw, (1030, 110, 1330, 200), (45, 20, 20), ACCENT_RED, radius=8)
    draw.text((1045, 122), "DECISION: BLOCK", fill=ACCENT_RED, font=f_box_title)
    draw.text((1045, 147), "Action prohibited by safety policy.\n• Terminate immediately\n• NEVER invokes execution handler\n• Record blocked audit record", fill=TEXT_MUTED, font=f_box_desc)

    # Blocked flow to Audit
    draw_arrow(draw, (1330, 155), (1390, 155), color=ACCENT_RED)

    # Branch B: ALLOW (Bottom Right)
    draw_arrow(draw, (960, 230), (1030, 230), color=ACCENT_GREEN)
    draw_rounded_card(draw, (1030, 210, 1330, 290), (20, 45, 30), ACCENT_GREEN, radius=8)
    draw.text((1045, 222), "DECISION: ALLOW", fill=ACCENT_GREEN, font=f_box_title)
    draw.text((1045, 247), "Explicit narrow rule matched.\n• Direct dispatch to executor\n• No human approval needed", fill=TEXT_MUTED, font=f_box_desc)

    # Branch C: ASK (Middle Downwards)
    draw_arrow(draw, (820, 260), (820, 340), color=ACCENT_AMBER)
    draw_rounded_card(draw, (660, 340, 980, 480), (30, 41, 59), ACCENT_AMBER, radius=8)
    draw.text((675, 355), "DECISION: ASK (Human Approval)", fill=ACCENT_AMBER, font=f_box_title)
    draw.text((675, 382), "Scoped Approval Manager:\n• Check for active, matching ApprovalRecord\n• Check expiry (300s TTL) & session binding\n• If valid token provided -> Validate & consume\n• If missing/invalid -> Request human approval", fill=TEXT_MUTED, font=f_box_desc)

    # Human Interaction Box
    draw_arrow(draw, (820, 480), (820, 540), color=ACCENT_AMBER)
    draw_rounded_card(draw, (620, 540, 1020, 710), (25, 35, 55), ACCENT_CYAN, radius=8)
    draw.text((635, 555), "4. INTERACTIVE HUMAN APPROVAL", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((635, 582), "Surfaced via Desktop UI:\n• Floating Hub badge: 'AgentGuard: 1 Awaiting Approval'\n• AgentGuard Panel: Approval Box with Approve / Reject\n• Scoped to exact target, operation, agent, and session\n\nUser Actions:\n[Approve (Single-Use)] -> Grants scoped token with TTL\n[Reject Action] -> Rejection recorded, execution cancelled", fill=TEXT_MUTED, font=f_box_desc)

    # Scope Mutation Protection Box (Callout)
    draw_rounded_card(draw, (50, 540, 560, 710), (40, 30, 20), (245, 158, 11), radius=8)
    draw.text((65, 555), "SECURITY GUARANTEE: SCOPE MUTATION", fill=(245, 158, 11), font=f_box_title)
    draw.text((65, 582), "Approvals are strictly non-transferable!\nIf any action parameter (target path, recipient,\noperation, untrusted context) mutates after approval\nis granted, validation fails immediately:\n-> Result: 'approval_scope_mismatch'\n-> Action halts; requires fresh human approval.\nNo blanket or permanent approvals in V1.", fill=TEXT_MUTED, font=f_box_desc)

    # Decision from approval
    # User rejects:
    draw_arrow(draw, (1020, 650), (1120, 650), color=ACCENT_RED)
    draw_rounded_card(draw, (1120, 620, 1340, 690), (45, 20, 20), ACCENT_RED, radius=8)
    draw.text((1135, 635), "USER REJECTED", fill=ACCENT_RED, font=f_box_title)
    draw.text((1135, 660), "Halt execution -> Log audit", fill=TEXT_MUTED, font=f_box_desc)

    # User approves / ALLOW flow to Controlled Executor
    draw_arrow(draw, (820, 710), (820, 770), color=ACCENT_GREEN)
    draw_arrow(draw, (1180, 290), (1180, 750), color=ACCENT_GREEN)
    draw.line([(1180, 750), (980, 750)], fill=ACCENT_GREEN, width=3)
    draw_arrow(draw, (980, 750), (860, 770), color=ACCENT_GREEN)

    # Step 5: Controlled Executor
    draw_rounded_card(draw, (620, 770, 1020, 890), (30, 41, 59), ACCENT_GREEN, radius=8)
    draw.text((635, 785), "5. CONTROLLED EXECUTOR (Gatekeeper)", fill=ACCENT_GREEN, font=f_box_title)
    draw.text((635, 812), "Enforces strict pre-execution gating:\n• Consumes approval token (single-use decrement)\n• Dispatches to safe mock handler (V1 demo)\n• Catches handler exceptions without leaking raw secret text\n• Produces ExecutionResult(status='executed'/'failed')", fill=TEXT_MUTED, font=f_box_desc)

    # Step 6: Local SQLite Audit Log (Right side common sink)
    draw_arrow(draw, (1020, 830), (1380, 830), color=ACCENT_CYAN)
    draw_arrow(draw, (1230, 690), (1420, 760), color=ACCENT_RED)
    draw_rounded_card(draw, (1380, 130, 1560, 940), (25, 35, 55), (59, 130, 246), radius=8)
    draw.text((1395, 150), "6. LOCAL SQLITE\nAUDIT LOG", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((1395, 210), "SqliteAuditLog\n\nSchema:\n• event_id (UUID)\n• timestamp\n• subsystem\n• event_type\n• severity\n• summary\n• payload_json\n• redacted (0/1)\n\nRedaction Policy:\nRaw secrets replaced\nwith [REDACTED_*].\nCleartext secrets\nnever persisted.\n\nPowers:\n• Latest 5 feed\n• Keyword search\n• Unified timeline", fill=TEXT_MUTED, font=get_font(11))

    out_file = OUT_DIR / "diagram_agentguard_workflow.png"
    img.save(out_file)
    print(f"Saved: {out_file}")

# -------------------------------------------------------------
# 3. CRASHGUARD DETAILED WORKFLOW FLOWCHART
# -------------------------------------------------------------
def generate_crashguard_workflow():
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    f_title = get_font(26, bold=True)
    f_sub = get_font(15, bold=False)
    f_box_title = get_font(15, bold=True)
    f_box_desc = get_font(12, bold=False)

    draw.text((50, 30), "CrashGuard — Operating System Telemetry, Sustained Risk & Recovery Flow", fill=TEXT_WHITE, font=f_title)
    draw.text((50, 68), "psutil Metrics -> Ring Buffer -> Sustained-Risk Detection -> Windows Evidence -> Safe Recovery Advisory -> Non-Modal Alert Popup", fill=TEXT_MUTED, font=f_sub)
    draw.line([(50, 95), (1550, 95)], fill=CARD_BORDER, width=2)

    # 1. Background Worker Loop
    draw_rounded_card(draw, (50, 130, 280, 290), (30, 41, 59), ACCENT_BLUE, radius=8)
    draw.text((65, 145), "1. MONITORING WORKER", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((65, 175), "Dedicated background thread:\n• Cadence: 2-10s configurable\n• Clean shutdown in < 2s\n• Non-blocking UI execution\n• Severe load backoff (>95% CPU\n  suppresses heavy diagnostics)\n• Bounded ring buffer (60 samples)", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (280, 210), (340, 210))

    # 2. Metrics Collector
    draw_rounded_card(draw, (340, 130, 600, 290), (30, 41, 59), (16, 185, 129), radius=8)
    draw.text((355, 145), "2. METRICS COLLECTOR", fill=(16, 185, 129), font=f_box_title)
    draw.text((355, 175), "Samples authentic OS metrics:\n• CPU utilization % (system & per-core)\n• RAM % & available physical bytes\n• Disk free bytes & busy percent\n• Top 5 processes (PID, name, CPU, RAM)\n• Honest reporting: unavailable counters\n  flagged in unavailable_metrics\n• Zero fabricated data in live mode", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (600, 210), (660, 210))

    # 3. Sustained Risk Detector
    draw_rounded_card(draw, (660, 120, 980, 320), (30, 41, 59), (234, 179, 8), radius=8)
    draw.text((675, 135), "3. SUSTAINED-RISK DETECTOR", fill=(234, 179, 8), font=f_box_title)
    draw.text((675, 162), "Evaluates SystemSnapshot against rules:\n• CPU >= 85% • RAM >= 85% • Disk Free < 5.0 GB\n\nSpike Filtering Axiom:\nTransient single spikes (< duration window) are ignored!\nCondition must persist across sustained window\n(default 10s demo / 30s prod) before alert triggers.\n\nAlert Cooldown & Transition Logic:\nEmits alert ONLY on transition into sustained risk.\nSuppresses duplicate alerts during continuous breach.", fill=TEXT_MUTED, font=f_box_desc)

    # Branch: Normal vs Risk
    draw_arrow(draw, (820, 320), (820, 380), color=ACCENT_CYAN)
    draw_rounded_card(draw, (660, 380, 980, 470), (20, 35, 45), ACCENT_CYAN, radius=8)
    draw.text((675, 395), "CONDITION EVALUATION", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((675, 422), "If Normal or Transient Spike -> Update Live Dashboard Gauges & Chart\nIf Sustained Breach Exceeded -> Transition to Alert & Recovery Pipeline", fill=TEXT_MUTED, font=f_box_desc)

    # Down to Pipeline
    draw_arrow(draw, (820, 470), (820, 520), color=ACCENT_AMBER)

    # 4. Windows Evidence Collector
    draw_rounded_card(draw, (50, 520, 450, 720), (30, 41, 59), (168, 85, 247), radius=8)
    draw.text((65, 535), "4. WINDOWS EVIDENCE COLLECTOR", fill=(168, 85, 247), font=f_box_title)
    draw.text((65, 565), "Queries Windows Event Logs:\n• ID 1000: Application Error (Crash)\n• ID 1002: Application Hang (Freeze)\n• ID 6008: Unexpected Shutdown\n\nObservation vs. Hypothesis Separation:\n• Confirmed Observation:\n  'Application Error recorded for app.exe at 14:02'\n• Suspected Hypothesis:\n  'app.exe may have encountered unhandled exception'\nGraceful degradation if unprivileged/non-Windows.", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (450, 620), (510, 620))

    # 5. Safe Recovery Advisor
    draw_rounded_card(draw, (510, 520, 950, 720), (30, 41, 59), (239, 68, 68), radius=8)
    draw.text((525, 535), "5. SAFE RECOVERY ADVISOR", fill=(239, 68, 68), font=f_box_title)
    draw.text((525, 565), "Formulates Non-Destructive Interventions:\n1. Universal Baseline: Save open files immediately\n2. High Memory: Highlight top consumer process;\n   suggest user manually close idle apps or browser tabs\n3. Sustained CPU: Identify runaway process;\n   allow compilation/render to finish or check loops\n4. Low Disk: Advise clearing temp caches or moving media\n\nNON-INTERFERENCE MANDATE (V1):\nis_automated = False on all recommendations!\nZERO process termination, suspend, or kill calls.", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (950, 620), (1010, 620))

    # 6. Desktop Alert Popup & UI Integration
    draw_rounded_card(draw, (1010, 500, 1550, 740), (25, 35, 55), (239, 68, 68), radius=8)
    draw.text((1025, 515), "6. CRASHGUARD ALERT POPUP (PySide6 QDialog)", fill=(239, 68, 68), font=f_box_title)
    draw.text((1025, 545), "• Non-blocking, non-modal, frameless top-level dialog\n• Window flag: WA_ShowWithoutActivating (never steals focus)\n• Combines multiple simultaneous threshold breaches into one card\n• Displays measured vs. threshold values with explicit units (%, GB)\n• Explicit badge: [SIMULATED DEMO ALERT] when triggered via demo\n• Explains trigger reason & displays safe recovery steps\n• Actions:\n  [View Details] -> Switches main window to CrashGuard dashboard\n  [Dismiss] -> Closes popup dialog without interrupting monitoring", fill=TEXT_MUTED, font=f_box_desc)

    # Bottom: Shared SQLite Event Store Ingestion
    draw_arrow(draw, (1280, 740), (1280, 800), color=ACCENT_CYAN)
    draw_rounded_card(draw, (50, 800, 1550, 950), (20, 30, 48), ACCENT_BLUE, radius=8)
    draw.text((70, 815), "UNIFIED PERSISTENCE & TIMELINE INTEGRATION (SQLite events table)", fill=ACCENT_BLUE, font=f_box_title)
    draw.text((70, 845), "• Persists RiskAlert as UnifiedEvent(subsystem='CrashGuard', event_type='SYSTEM_ALERT', severity='warning'|'critical')\n• Correlates with AgentGuard security events by timestamp\n• Surfaced in Unified Timeline tab with search & filter\n• Prominent Disclaimer: 'Temporal correlation between agent actions and resource pressure provides investigative context, not proof of causation.'", fill=TEXT_MUTED, font=f_box_desc)

    out_file = OUT_DIR / "diagram_crashguard_workflow.png"
    img.save(out_file)
    print(f"Saved: {out_file}")

# -------------------------------------------------------------
# 4. SHARED STORAGE & UI INTEGRATION DIAGRAM
# -------------------------------------------------------------
def generate_storage_ui_integration():
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    f_title = get_font(26, bold=True)
    f_sub = get_font(15, bold=False)
    f_box_title = get_font(15, bold=True)
    f_box_desc = get_font(12, bold=False)

    draw.text((50, 30), "SENTRON V1 — Shared Event Storage & Multi-Panel Desktop UI Integration", fill=TEXT_WHITE, font=f_title)
    draw.text((50, 68), "Unified SQLite Storage • Qt Signal Architecture • Floating Hub Synchronization • Responsive Layouts & Trend Visualization", fill=TEXT_MUTED, font=f_sub)
    draw.line([(50, 95), (1550, 95)], fill=CARD_BORDER, width=2)

    # Left: Database Layer
    draw_rounded_card(draw, (50, 130, 480, 520), (30, 41, 59), (245, 158, 11), radius=10)
    draw.text((70, 145), "LOCAL SQLITE EVENT STORE", fill=(245, 158, 11), font=f_box_title)
    draw.text((70, 175), "sentron.core.storage.EventStore\n\nSchema: events table\n• event_id TEXT PRIMARY KEY\n• timestamp REAL NOT NULL\n• subsystem TEXT NOT NULL\n• event_type TEXT NOT NULL\n• severity TEXT NOT NULL\n• summary TEXT NOT NULL\n• payload_json TEXT NOT NULL\n• redacted INTEGER DEFAULT 0\n\nIndexes:\n• idx_events_timestamp\n• idx_events_subsystem\n• idx_events_event_type\n\nData Governance:\n• Redacts detected API keys/secrets\n• Configurable purge_older_than(days)\n• Zero remote database or cloud sync", fill=TEXT_MUTED, font=f_box_desc)

    # Ingestion sources to DB
    draw_rounded_card(draw, (50, 560, 480, 720), (20, 30, 48), ACCENT_BLUE, radius=8)
    draw.text((70, 575), "DUAL INGESTION STREAMS", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((70, 605), "1. AgentGuard Audit Logger:\n   Policy evaluations, approvals, rejections,\n   and execution outcomes.\n2. CrashGuard System Alerts:\n   Threshold crossings, sustained pressure,\n   and recovery recommendations.", fill=TEXT_MUTED, font=f_box_desc)
    draw_arrow(draw, (265, 560), (265, 520), color=ACCENT_CYAN)

    # Middle: Qt Signal Dispatcher
    draw_rounded_card(draw, (540, 130, 880, 520), (30, 41, 59), ACCENT_CYAN, radius=10)
    draw.text((555, 145), "QT SIGNAL BUS & ROUTING", fill=ACCENT_CYAN, font=f_box_title)
    draw.text((555, 175), "Thread-Safe UI Communication:\n\n• snapshot_received(SystemSnapshot):\n  Emitted by MonitoringWorker thread.\n  Routes to CrashGuardPanel for gauges\n  and QPainter rolling chart updates.\n  Routes to FloatingHubWidget.\n\n• alert_received(RiskAlert, list):\n  Emitted on sustained threshold transition.\n  Spawns CrashGuardAlertPopup dialog.\n  Persists SYSTEM_ALERT to SQLite.\n\n• event_recorded():\n  Emitted on new AgentGuard action.\n  Triggers timeline table refresh.", fill=TEXT_MUTED, font=f_box_desc)

    draw_arrow(draw, (480, 325), (540, 325), color=(245, 158, 11))
    draw_arrow(draw, (880, 220), (940, 220), color=ACCENT_CYAN)
    draw_arrow(draw, (880, 420), (940, 420), color=ACCENT_CYAN)

    # Right Top: Floating Hub Widget
    draw_rounded_card(draw, (940, 130, 1550, 330), (20, 30, 48), ACCENT_BLUE, radius=10)
    draw.text((955, 145), "MOVABLE FLOATING DESKTOP HUB (Qt.Tool / Always-on-top)", fill=ACCENT_BLUE, font=f_box_title)
    draw.text((955, 175), "• Draggable to any screen corner; low screen real-estate overhead\n• Live Status Display: 'PROTECTED' (green) or 'DEGRADED' (amber/red)\n• AgentGuard Status: '0 Pending (Safe)' or '1 Awaiting Approval'\n• CrashGuard Status: Live CPU % & RAM % telemetry\n• Honest Availability Guarantee: If worker stopped, displays 'Inactive', NEVER 'Active'\n• Toggle Button: Brings main dashboard window into view", fill=TEXT_MUTED, font=f_box_desc)

    # Right Bottom: Main Dashboard Tabs
    draw_rounded_card(draw, (940, 360, 1550, 720), (30, 41, 59), (16, 185, 129), radius=10)
    draw.text((955, 375), "MAIN APPLICATION WINDOW (PySide6 QMainWindow)", fill=(16, 185, 129), font=f_box_title)
    draw.text((955, 405), "Responsive layout (min 880x540, default 1160x680, scroll areas prevent clipping):\n\nTab 1: Live Security & Health Dashboard (Splitter)\n• Left Panel: AgentGuard Scenario Runner, Risk Findings, Scoped Approval Box\n• Right Panel: CrashGuard Live Hardware Gauges, Top Processes Table,\n  Safe Recovery Recommendations, QPainter Rolling Trend Chart (60 samples)\n\nTab 2: Unified Timeline & Temporal Search\n• Correlates AgentGuard & CrashGuard events in single chronological feed\n• Full-text keyword search across summary, event_type, and payload\n• Prominent Disclaimer: 'Temporal correlation does not imply causation.'", fill=TEXT_MUTED, font=f_box_desc)

    # Bottom: Alert Popup Dialog callout
    draw_rounded_card(draw, (540, 560, 880, 720), (45, 20, 20), (239, 68, 68), radius=8)
    draw.text((555, 575), "ALERT POPUP INTEGRATION", fill=(239, 68, 68), font=f_box_title)
    draw.text((555, 605), "• Non-modal, non-focus-stealing\n• Combines simultaneous resource breaches\n• Shows measured vs. threshold with units\n• [View Details] switches window to Tab 1\n• [Dismiss] closes popup safely", fill=TEXT_MUTED, font=f_box_desc)

    # Footer banner
    draw_rounded_card(draw, (50, 760, 1550, 950), (20, 30, 48), CARD_BORDER, radius=10)
    draw.text((70, 780), "SYSTEM ARCHITECTURAL HIGHLIGHTS & SAFETY ASSURANCES", fill=TEXT_WHITE, font=f_box_title)
    draw.text((70, 815), "1. Modular Monolith Architecture: Decoupled Python packages under sentron.* eliminate IPC latency and port conflicts.\n2. Complete Offline Operation: 0 external AI SDKs, 0 cloud telemetry calls, 0 mandatory internet connection (verified by AC-18).\n3. Deterministic Safety Gating: Blocked actions NEVER reach executor. Approval must be scoped, expiring, single-use, and session-bound.\n4. Non-Interference Mandate: CrashGuard NEVER automatically terminates or suspends processes. Advises safe user interventions.\n5. Telemetry Integrity: Real measurements collected via psutil. Simulated demo alerts are explicitly badged [SIMULATED DEMO ALERT].", fill=TEXT_MUTED, font=f_box_desc)

    out_file = OUT_DIR / "diagram_storage_ui_integration.png"
    img.save(out_file)
    print(f"Saved: {out_file}")

if __name__ == "__main__":
    generate_system_architecture()
    generate_agentguard_workflow()
    generate_crashguard_workflow()
    generate_storage_ui_integration()
    print("All architectural diagrams generated successfully!")

"""
Synthetic SOC data generator.

Generates realistic (and deliberately imperfect) CSV datasets for the
SOC Control Effectiveness & Business Risk Platform.

Design assumptions (documented per project instructions):
- We generate TWO time periods per asset/control combination: a BASELINE
  period (~90 days ago) and a CURRENT/POST-CONTROL period (recent), so the
  control-effectiveness and risk-reduction experiment has real before/after
  data to compare, rather than inventing two arbitrary numbers.
- Data quality problems (missing values, duplicates, stale timestamps,
  invalid percentages, inconsistent statuses) are injected at a known,
  fixed rate (see INJECT_RATE) so validation/tests have deterministic
  targets to catch.
- Output: CSV files under data/processed/, which the backend's
  ingestion pipeline (backend/app/services/ingestion.py) loads into
  PostgreSQL (or SQLite fallback) via SQLAlchemy.

Run:
    python data/generate_data.py
"""

import csv
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

random.seed(42)  # reproducibility

OUT_DIR = os.path.join(os.path.dirname(__file__), "processed")
os.makedirs(OUT_DIR, exist_ok=True)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
BASELINE_ANCHOR = NOW - timedelta(days=90)

INJECT_RATE = 0.06  # ~6% of records get a deliberate data-quality issue

ASSET_TYPES = ["Laptop", "Desktop", "Server", "Database", "Cloud VM", "Container", "Application", "Network Device"]
BUSINESS_UNITS = ["Finance", "HR", "Engineering", "Sales", "Operations", "Customer Support", "Legal"]
ENVIRONMENTS = ["Production", "Staging", "Development"]
CRITICALITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CRITICALITY_SCORE = {"LOW": 20, "MEDIUM": 45, "HIGH": 70, "CRITICAL": 95}
OS_LIST = ["Windows 10", "Windows 11", "Windows Server 2019", "Windows Server 2022",
           "Ubuntu 22.04", "RHEL 8", "macOS Sonoma", "Amazon Linux 2"]

CONTROL_DEFS = [
    ("EDR", "Endpoint Detection and Response", "Detective"),
    ("MFA", "Multi-Factor Authentication", "Preventive"),
    ("PATCH", "Vulnerability Patching", "Corrective"),
    ("EMAILSEC", "Email Security", "Preventive"),
    ("FW", "Firewall", "Preventive"),
    ("BACKUP", "Backup", "Corrective"),
    ("IAM", "Identity Access Control", "Preventive"),
    ("CLOUDSEC", "Cloud Security Monitoring", "Detective"),
    ("AWARE", "Security Awareness Training", "Preventive"),
]

VULN_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_CVSS_RANGE = {"LOW": (0.1, 3.9), "MEDIUM": (4.0, 6.9), "HIGH": (7.0, 8.9), "CRITICAL": (9.0, 10.0)}

INCIDENT_TYPES = ["Malware", "Phishing", "Credential Compromise", "Unauthorized Access",
                   "Data Leakage", "Ransomware Simulation", "Cloud Misconfiguration", "Suspicious Activity"]

N_ASSETS = 220
N_CONTROLS = len(CONTROL_DEFS)


def maybe_corrupt(value, kind, issues_log, record_id, source_table):
    """Randomly inject a data-quality issue and log it for later validation testing."""
    if random.random() < INJECT_RATE:
        issue = random.choice(["missing", "invalid", "stale"]) if kind == "generic" else kind
        issues_log.append({"source_table": source_table, "record_id": record_id, "issue_type": issue})
        if issue == "missing":
            return ""
        if issue == "invalid" and isinstance(value, (int, float)):
            return value * -1 if random.random() < 0.5 else value + 1000
        if issue == "stale":
            return (NOW - timedelta(days=random.randint(30, 400))).isoformat()
    return value


def gen_assets():
    rows = []
    for i in range(1, N_ASSETS + 1):
        asset_id = f"AST-{i:05d}"
        criticality = random.choices(CRITICALITY_LEVELS, weights=[35, 35, 20, 10])[0]
        last_seen = NOW - timedelta(minutes=random.randint(1, 60 * 24 * 10))
        rows.append({
            "asset_id": asset_id,
            "asset_name": f"{random.choice(BUSINESS_UNITS)}-{random.choice(ASSET_TYPES).replace(' ', '')}-{i}",
            "asset_type": random.choice(ASSET_TYPES),
            "business_unit": random.choice(BUSINESS_UNITS),
            "environment": random.choice(ENVIRONMENTS),
            "owner": f"owner{random.randint(1, 40)}@example.com",
            "criticality": criticality,
            "criticality_score": CRITICALITY_SCORE[criticality],
            "internet_exposed": random.random() < 0.22,
            "operating_system": random.choice(OS_LIST),
            "last_seen": last_seen.isoformat(),
        })
    return rows


def gen_controls():
    rows = []
    for code, name, ctype in CONTROL_DEFS:
        target = random.choice([90, 92, 95, 98])
        # actual coverage: baseline lower, "current" simulated as improved -> we store the
        # CURRENT actual_coverage here; historical telemetry captures the trajectory.
        actual = round(min(100, target - random.uniform(2, 6)), 1)
        rows.append({
            "control_id": f"CTRL-{code}",
            "control_name": name,
            "control_type": ctype,
            "description": f"{name} control covering enterprise assets.",
            "target_coverage": target,
            "actual_coverage": actual,
            "status": "ACTIVE",
            "implementation_date": (BASELINE_ANCHOR - timedelta(days=random.randint(30, 400))).date().isoformat(),
            "owner": f"{ctype.lower()}-team@example.com",
        })
    return rows


def gen_control_telemetry(assets, controls, issues_log):
    """For each asset x control, generate a BASELINE telemetry row and a CURRENT row,
    with coverage/compliance improving over time (simulating control rollout)."""
    rows = []
    for control in controls:
        # controls don't apply to 100% of assets uniformly (e.g. network device controls skew infra)
        applicable_assets = random.sample(assets, k=int(len(assets) * random.uniform(0.55, 0.95)))
        for asset in applicable_assets:
            base_coverage = random.uniform(45, 75)
            improvement = random.uniform(15, 40)
            current_coverage = min(100, base_coverage + improvement)

            base_compliance = random.uniform(40, 70)
            current_compliance = min(100, base_compliance + random.uniform(15, 35))

            for period, ts, coverage, compliance in [
                ("BASELINE", BASELINE_ANCHOR + timedelta(days=random.randint(0, 5)), base_coverage, base_compliance),
                ("CURRENT", NOW - timedelta(hours=random.randint(0, 240)), current_coverage, current_compliance),
            ]:
                tid = f"TEL-{uuid.uuid4().hex[:12]}"
                coverage_val = maybe_corrupt(round(coverage, 1), "generic", issues_log, tid, "control_telemetry")
                freshness = ts
                # stale injection: push freshness far into the past for ~5% of CURRENT rows
                if period == "CURRENT" and random.random() < 0.05:
                    freshness = NOW - timedelta(days=random.randint(8, 30))
                    issues_log.append({"source_table": "control_telemetry", "record_id": tid, "issue_type": "stale"})
                rows.append({
                    "telemetry_id": tid,
                    "control_id": control["control_id"],
                    "asset_id": asset["asset_id"],
                    "timestamp": ts.isoformat(),
                    "coverage_percentage": coverage_val,
                    "compliance_percentage": round(compliance, 1),
                    "health_status": random.choices(["HEALTHY", "DEGRADED", "FAILED"], weights=[80, 15, 5])[0],
                    "event_count": random.randint(0, 500),
                    "source": random.choice(["agent", "cloud_api", "syslog"]),
                    "data_quality": random.choices(["GOOD", "DEGRADED", "BAD"], weights=[85, 12, 3])[0],
                    "freshness_timestamp": freshness.isoformat(),
                    "period": period,
                })
    return rows


def gen_vulnerabilities(assets, issues_log):
    rows = []
    vid = 1
    for asset in assets:
        # more critical/exposed assets get more vulns
        base_n = 1 if asset["criticality"] in ("LOW", "MEDIUM") else 2
        exposure_bonus = 2 if asset["internet_exposed"] else 0
        n = random.randint(0, base_n + exposure_bonus + 2)
        for _ in range(n):
            severity = random.choices(VULN_SEVERITIES, weights=[30, 35, 25, 10])[0]
            lo, hi = SEVERITY_CVSS_RANGE[severity]
            discovered = BASELINE_ANCHOR - timedelta(days=random.randint(0, 60))
            due = discovered + timedelta(days=random.choice([15, 30, 60, 90]))
            # baseline-era vuln: some remain open (post-control), some get fixed
            fixed = random.random() < 0.65
            remediation_date = None
            if fixed:
                remediation_date = discovered + timedelta(days=random.randint(5, 85))
                status = "REMEDIATED" if remediation_date < NOW else "IN_PROGRESS"
            else:
                status = random.choices(["OPEN", "IN_PROGRESS", "ACCEPTED_RISK"], weights=[60, 30, 10])[0]

            vuln_id = f"VUL-{vid:06d}"
            vid += 1
            cvss = maybe_corrupt(round(random.uniform(lo, hi), 1), "generic", issues_log, vuln_id, "vulnerabilities")
            rows.append({
                "vulnerability_id": vuln_id,
                "asset_id": asset["asset_id"],
                "cve_id": f"CVE-2025-{random.randint(1000, 59999)}",
                "severity": severity,
                "cvss_score": cvss,
                "discovered_date": discovered.date().isoformat(),
                "due_date": due.date().isoformat(),
                "remediation_status": status,
                "remediation_date": remediation_date.date().isoformat() if remediation_date else "",
                "exploit_available": random.random() < 0.25,
                "internet_exposed": asset["internet_exposed"],
                "business_impact": asset["criticality"],
            })
    return rows


def gen_incidents(assets, controls, issues_log):
    rows = []
    iid = 1
    # baseline period has more incidents than current period (controls working)
    for period, window_start, window_end, rate in [
        ("BASELINE", BASELINE_ANCHOR - timedelta(days=20), BASELINE_ANCHOR, 1.0),
        ("CURRENT", NOW - timedelta(days=30), NOW, 0.55),
    ]:
        n_incidents = int(len(assets) * 0.18 * rate)
        for _ in range(n_incidents):
            asset = random.choice(assets)
            severity = random.choices(["LOW", "MEDIUM", "HIGH", "CRITICAL"], weights=[35, 35, 20, 10])[0]
            detected = window_start + (window_end - window_start) * random.random()
            resolved = detected + timedelta(hours=random.randint(1, 96)) if random.random() < 0.85 else None
            incident_id = f"INC-{iid:06d}"
            iid += 1
            related_control = random.choice(controls)["control_id"] if random.random() < 0.7 else ""
            rows.append({
                "incident_id": incident_id,
                "asset_id": asset["asset_id"],
                "incident_type": random.choice(INCIDENT_TYPES),
                "severity": severity,
                "detected_at": detected.isoformat(),
                "resolved_at": resolved.isoformat() if resolved else "",
                "status": "RESOLVED" if resolved else "OPEN",
                "root_cause": random.choice(["Unpatched vulnerability", "Phishing click", "Misconfiguration",
                                              "Weak credentials", "Third-party compromise", "Unknown"]),
                "control_related": related_control,
                "business_impact": asset["criticality"],
                "financial_impact_estimate": round(random.uniform(500, 50000), 2)
                    if severity in ("HIGH", "CRITICAL") else round(random.uniform(0, 3000), 2),
                "period": period,
            })
    # inject a handful of exact duplicates
    for _ in range(6):
        dup = dict(random.choice(rows))
        issues_log.append({"source_table": "incidents", "record_id": dup["incident_id"], "issue_type": "duplicate"})
        rows.append(dup)
    return rows


def gen_remediation(vulnerabilities):
    rows = []
    rid = 1
    for v in vulnerabilities:
        if v["remediation_status"] in ("REMEDIATED", "IN_PROGRESS"):
            assigned = datetime.fromisoformat(v["discovered_date"]) + timedelta(days=random.randint(0, 3))
            due = datetime.fromisoformat(v["due_date"])
            completed = v["remediation_date"]
            rows.append({
                "remediation_id": f"REM-{rid:06d}",
                "vulnerability_id": v["vulnerability_id"],
                "asset_id": v["asset_id"],
                "assigned_to": f"engineer{random.randint(1, 25)}@example.com",
                "assigned_date": assigned.date().isoformat(),
                "due_date": due.date().isoformat(),
                "completed_date": completed,
                "status": "COMPLETE" if completed else "IN_PROGRESS",
                "verification_status": random.choices(["VERIFIED", "UNVERIFIED"], weights=[75, 25])[0] if completed else "PENDING",
            })
            rid += 1
    return rows


def gen_legacy_cases(assets):
    rows = []
    for i in range(1, 141):
        created = BASELINE_ANCHOR - timedelta(days=random.randint(0, 120))
        migrated = random.random() < 0.7
        rows.append({
            "legacy_case_id": f"LEG-{i:05d}",
            "alert_id": f"ALERT-{random.randint(10000, 99999)}",
            "created_at": created.isoformat(),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "analyst": f"analyst{random.randint(1, 12)}@example.com",
            "status": random.choice(["CLOSED", "OPEN", "ESCALATED"]),
            "resolution": random.choice(["False positive", "Confirmed - remediated", "Confirmed - accepted risk", ""]),
            "migrated": migrated,
            "migration_timestamp": (created + timedelta(days=random.randint(1, 30))).isoformat() if migrated else "",
        })
    return rows


def write_csv(rows, filename, fieldnames=None):
    path = os.path.join(OUT_DIR, filename)
    if not rows:
        return path
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return path


def main():
    issues_log = []

    assets = gen_assets()
    controls = gen_controls()
    telemetry = gen_control_telemetry(assets, controls, issues_log)
    vulnerabilities = gen_vulnerabilities(assets, issues_log)
    incidents = gen_incidents(assets, controls, issues_log)
    remediation = gen_remediation(vulnerabilities)
    legacy_cases = gen_legacy_cases(assets)

    write_csv(assets, "assets.csv")
    write_csv(controls, "controls.csv")
    write_csv(telemetry, "control_telemetry.csv")
    write_csv(vulnerabilities, "vulnerabilities.csv")
    write_csv(incidents, "incidents.csv")
    write_csv(remediation, "remediation.csv")
    write_csv(legacy_cases, "legacy_cases.csv")
    write_csv(issues_log, "_injected_data_quality_issues.csv",
              fieldnames=["source_table", "record_id", "issue_type"])

    print(f"Generated: {len(assets)} assets, {len(controls)} controls, "
          f"{len(telemetry)} telemetry rows, {len(vulnerabilities)} vulnerabilities, "
          f"{len(incidents)} incidents, {len(remediation)} remediation records, "
          f"{len(legacy_cases)} legacy cases.")
    print(f"Injected {len(issues_log)} known data-quality issues for validation testing.")
    print(f"Output directory: {OUT_DIR}")


if __name__ == "__main__":
    main()

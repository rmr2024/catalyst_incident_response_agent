import re

from schemas import Alert
from settings import settings

P1_WORDS = ("down", "outage", "5xx", "unreachable")
P2_WORDS = ("exhaust", "leak", "timeout", "degrad", "saturat", "stampede")


def _num(metrics: dict, key: str) -> float | None:
    try:
        v = metrics.get(key)
        return None if v is None or isinstance(v, bool) else float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v: float) -> str:
    return f"{v:g}"


def is_critical(alert: Alert) -> bool:
    crit = settings.critical_list
    if alert.service.strip().lower() in crit:
        return True
    words = set(re.findall(r"[a-z0-9\-]+", alert.message.lower()))
    return any(c in words for c in crit)


def classify(alert: Alert) -> tuple[str, str]:
    if alert.severity:
        return alert.severity, "provided by source"
    m = alert.metrics or {}
    msg = alert.message.lower()
    er, users, avail = _num(m, "error_rate"), _num(m, "affected_users"), _num(m, "availability")
    p99, cpu, mem = _num(m, "latency_p99_ms"), _num(m, "cpu"), _num(m, "memory")
    critical = is_critical(alert)
    crit_note = f"critical service {alert.service}"

    r1 = []
    if er is not None and er >= 0.2:
        r1.append(f"error_rate {_fmt(er)} ≥ 0.2")
    if users is not None and users >= 10000:
        r1.append(f"affected_users {_fmt(users)} ≥ 10000")
    if avail is not None and avail < 0.95:
        r1.append(f"availability {_fmt(avail)} < 0.95")
    if critical:
        hits = [w for w in P1_WORDS if w in msg]
        if er is not None and er >= 0.05:
            r1.append(f"{crit_note} with error_rate {_fmt(er)} ≥ 0.05")
        elif hits:
            r1.append(f"{crit_note} reports '{hits[0]}'")
    if r1:
        if critical and not any(crit_note in r for r in r1):
            r1.append(crit_note)
        return "P1", "; ".join(r1)

    r2 = []
    if er is not None and er >= 0.05:
        r2.append(f"error_rate {_fmt(er)} ≥ 0.05")
    if users is not None and users >= 1000:
        r2.append(f"affected_users {_fmt(users)} ≥ 1000")
    if p99 is not None and p99 >= 2000:
        r2.append(f"latency_p99_ms {_fmt(p99)} ≥ 2000")
    if cpu is not None and cpu >= 90:
        r2.append(f"cpu {_fmt(cpu)} ≥ 90")
    if mem is not None and mem >= 90:
        r2.append(f"memory {_fmt(mem)} ≥ 90")
    if critical:
        r2.append(crit_note)
    kw = [w for w in P2_WORDS if w in msg]
    if kw:
        r2.append(f"message mentions '{kw[0]}'")
    if r2:
        return "P2", "; ".join(r2)
    return "P3", "no thresholds breached"

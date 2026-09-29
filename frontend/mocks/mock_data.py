"""
Realistic mock data fixtures matching hackathon operational scenarios.
Covers:
1. Active incidents
2. Resolved incidents
3. P1/P2/P3 incidents
4. Database pool exhaustion
5. Memory leak
6. Bad deployment
7. Cache stampede
8. Novel incident
9. Similar incidents
10. Root causes
11. Recommendations
12. Timeline events
"""

from typing import Any, Dict, List

MOCK_STATS: Dict[str, Any] = {
    "total": 18,
    "active": 3,
    "p1": 2,
    "p2": 1,
    "p3": 0,
    "avg_ttr_minutes": 13.8,
    "resolved_today": 15,
}

# 9. Similar Incidents & 10. Historical Root Causes
MOCK_SIMILAR_INCIDENTS: List[Dict[str, Any]] = [
    {
        "incidentId": "INC-104",
        "incident_id": "INC-104",
        "similarity": 0.94,
        "outcome": "worked",
        "rootCause": "Database connection pool saturation under high checkout volume",
        "root_cause": "Database connection pool saturation under high checkout volume",
        "resolution": "Increased connection pool capacity from 50 to 150 and restarted connection manager.",
    },
    {
        "incidentId": "INC-117",
        "incident_id": "INC-117",
        "similarity": 0.89,
        "outcome": "worked",
        "rootCause": "Leaked unclosed sessions in payment worker routine",
        "root_cause": "Leaked unclosed sessions in payment worker routine",
        "resolution": "Ran DB-POOL-RECOVERY runbook and patched connection context manager.",
    },
    {
        "incidentId": "INC-089",
        "incident_id": "INC-089",
        "similarity": 0.76,
        "outcome": "failed",
        "rootCause": "Database connection starvation",
        "root_cause": "Database connection starvation",
        "resolution": "Restarted API pods without increasing pool size (failed within 5 minutes).",
    },
]

# 11. Recommendations & Root Cause Hypotheses
MOCK_RECOMMENDATION_DB_POOL: Dict[str, Any] = {
    "hypothesis": "Database connection pool exhaustion caused by high concurrent checkout requests",
    "confidence": 0.94,
    "evidence": [
        "INC-104 exhibited identical 503 spike and PostgreSQL pool error logs",
        "DB-POOL-RECOVERY runbook successfully resolved INC-104 and INC-117",
        "Connection leak detected in checkout handler routine",
    ],
    "recommendedSteps": [
        "Run DB-POOL-RECOVERY runbook to dynamically expand pool capacity",
        "Gracefully restart payments-db connection pool manager",
        "Verify active client connections normalize below 70% threshold",
    ],
    "recommended_steps": [
        "Run DB-POOL-RECOVERY runbook to dynamically expand pool capacity",
        "Gracefully restart payments-db connection pool manager",
        "Verify active client connections normalize below 70% threshold",
    ],
    "runbook": "DB-POOL-RECOVERY",
    "failedBefore": [
        "Simple application container restart failed in INC-089 because pool capacity was not increased.",
    ],
    "failed_before": [
        "Simple application container restart failed in INC-089 because pool capacity was not increased.",
    ],
    "previous_successful_fix": "Increased connection pool capacity from 50 to 150 and restarted connection manager (from INC-104).",
    "previousSuccessfulFix": "Increased connection pool capacity from 50 to 150 and restarted connection manager (from INC-104).",
    "needsApproval": True,
    "needs_approval": True,
    "whatsDifferent": "Current traffic has 15% higher write volume than INC-104.",
    "isNovel": False,
    "is_novel": False,
}

MOCK_RECOMMENDATION_CACHE: Dict[str, Any] = {
    "hypothesis": "Redis token cache eviction causing stampede to backing database",
    "confidence": 0.88,
    "evidence": [
        "Cache miss rate spiked from 4% to 82% at 11:42Z",
        "Matches INC-142 Redis key expiry pattern",
    ],
    "recommendedSteps": [
        "Execute CACHE-WARM-RESEED runbook to rebuild token cache in batches",
        "Enable probabilistic early cache expiration on auth nodes",
        "Verify cache miss rate drops below 10%",
    ],
    "recommended_steps": [
        "Execute CACHE-WARM-RESEED runbook to rebuild token cache in batches",
        "Enable probabilistic early cache expiration on auth nodes",
        "Verify cache miss rate drops below 10%",
    ],
    "runbook": "CACHE-WARM-RESEED",
    "failedBefore": [
        "Flushing redis cluster worsened database CPU load in INC-131.",
    ],
    "failed_before": [
        "Flushing redis cluster worsened database CPU load in INC-131.",
    ],
    "previous_successful_fix": "Warmed token cache in batches from replica and applied TTL jitter (from INC-142).",
    "previousSuccessfulFix": "Warmed token cache in batches from replica and applied TTL jitter (from INC-142).",
    "needsApproval": True,
    "needs_approval": True,
    "whatsDifferent": "Token cluster has 3 additional replica nodes since INC-142.",
    "isNovel": False,
    "is_novel": False,
}

MOCK_RECOMMENDATION_DEPLOY: Dict[str, Any] = {
    "hypothesis": "Invalid routing configuration in canary deployment v3.2.1 causing HTTP 502 Bad Gateway",
    "confidence": 0.96,
    "evidence": [
        "Canary release v3.2.1 deployed 8 minutes before 502 spike",
        "Envoy proxy upstream connection reset logs matching INC-062",
    ],
    "recommendedSteps": [
        "Execute DEPLOY-ROLLBACK-PREV runbook to revert traffic to v3.2.0",
        "Drain traffic from canary pods",
        "Verify HTTP 502 rate drops to 0%",
    ],
    "recommended_steps": [
        "Execute DEPLOY-ROLLBACK-PREV runbook to revert traffic to v3.2.0",
        "Drain traffic from canary pods",
        "Verify HTTP 502 rate drops to 0%",
    ],
    "runbook": "DEPLOY-ROLLBACK-PREV",
    "failedBefore": [
        "Attempting in-place patch without rolling back prolonged outage by 25 minutes in INC-041.",
    ],
    "failed_before": [
        "Attempting in-place patch without rolling back prolonged outage by 25 minutes in INC-041.",
    ],
    "previous_successful_fix": "Executed automated canary rollback DEPLOY-ROLLBACK-PREV (from INC-062).",
    "previousSuccessfulFix": "Executed automated canary rollback DEPLOY-ROLLBACK-PREV (from INC-062).",
    "needsApproval": True,
    "needs_approval": True,
    "whatsDifferent": "Deployment used blue/green routing switch.",
    "isNovel": False,
    "is_novel": False,
}

MOCK_RECOMMENDATION_MEMORY_LEAK: Dict[str, Any] = {
    "hypothesis": "Unbounded in-memory LRU cache retention in worker routine causing progressive heap exhaustion",
    "confidence": 0.92,
    "evidence": [
        "Heap profile matches INC-102 leak pattern exactly",
        "OOMKilled pod restart frequency matches INC-102",
        "MEM-LEAK-ROLLBACK previously resolved INC-102",
    ],
    "recommendedSteps": [
        "Execute MEM-LEAK-ROLLBACK to revert to stable container image v3.2.9",
        "Enable heap dump diagnostic logging on canary instance",
        "Verify memory consumption stabilizes below 60%",
    ],
    "recommended_steps": [
        "Execute MEM-LEAK-ROLLBACK to revert to stable container image v3.2.9",
        "Enable heap dump diagnostic logging on canary instance",
        "Verify memory consumption stabilizes below 60%",
    ],
    "runbook": "MEM-LEAK-ROLLBACK",
    "failedBefore": [
        "Increasing pod memory limit to 4Gi in INC-078 only delayed OOMKill without fixing root cause.",
    ],
    "failed_before": [
        "Increasing pod memory limit to 4Gi in INC-078 only delayed OOMKill without fixing root cause.",
    ],
    "previous_successful_fix": "Rolled back to previous stable release and configured TTL cache eviction (from INC-102).",
    "previousSuccessfulFix": "Rolled back to previous stable release and configured TTL cache eviction (from INC-102).",
    "needsApproval": True,
    "needs_approval": True,
    "isNovel": False,
    "is_novel": False,
}

MOCK_RECOMMENDATION_NOVEL: Dict[str, Any] = {
    "hypothesis": "Unprecedented upstream partner TLS handshake freeze without TCP read timeout (Novel Incident)",
    "confidence": 0.61,
    "evidence": [
        "Hindsight memory search returned zero matches above 60% similarity threshold",
        "First-time failure signature on shipping-gateway",
        "Socket thread dump confirms 48 worker threads blocked in SSL_connect",
    ],
    "recommendedSteps": [
        "Configure explicit socket read timeout of 5s on partner connection pool",
        "Temporarily route shipments to secondary carrier",
        "Escalate to on-call engineer for novel failure review",
    ],
    "recommended_steps": [
        "Configure explicit socket read timeout of 5s on partner connection pool",
        "Temporarily route shipments to secondary carrier",
        "Escalate to on-call engineer for novel failure review",
    ],
    "runbook": "NOVEL-INCIDENT-TRIAGE",
    "failedBefore": [
        "No previous recorded failure modes found in memory for this pattern.",
    ],
    "failed_before": [
        "No previous recorded failure modes found in memory for this pattern.",
    ],
    "previous_successful_fix": "None (First-time novel failure — no prior historical precedent exists in memory).",
    "previousSuccessfulFix": "None (First-time novel failure — no prior historical precedent exists in memory).",
    "needsApproval": True,
    "needs_approval": True,
    "isNovel": True,
    "is_novel": True,
}

MOCK_SIMILAR_INCIDENTS_MEMORY_LEAK: List[Dict[str, Any]] = [
    {
        "incidentId": "INC-102",
        "incident_id": "INC-102",
        "similarity": 0.92,
        "outcome": "worked",
        "rootCause": "Unbounded autocomplete in-memory cache retention in release v3.3.0",
        "root_cause": "Unbounded autocomplete in-memory cache retention in release v3.3.0",
        "resolution": "Rolled back to v3.2.9 via MEM-LEAK-ROLLBACK and added TTL eviction.",
    },
    {
        "incidentId": "INC-111",
        "incident_id": "INC-111",
        "similarity": 0.87,
        "outcome": "worked",
        "rootCause": "Worker routine goroutine leak holding unclosed request buffers",
        "root_cause": "Worker routine goroutine leak holding unclosed request buffers",
        "resolution": "Patched request context cancellation and restarted pods.",
    },
]

MOCK_SIMILAR_INCIDENTS_DEPLOY: List[Dict[str, Any]] = [
    {
        "incidentId": "INC-062",
        "incident_id": "INC-062",
        "similarity": 0.95,
        "outcome": "worked",
        "rootCause": "Canary Envoy proxy TLS config regression",
        "root_cause": "Canary Envoy proxy TLS config regression",
        "resolution": "Rolled back to previous stable release via DEPLOY-ROLLBACK-PREV.",
    },
    {
        "incidentId": "INC-105",
        "incident_id": "INC-105",
        "similarity": 0.91,
        "outcome": "worked",
        "rootCause": "Missing required currency_code validation in payment gateway release",
        "root_cause": "Missing required currency_code validation in payment gateway release",
        "resolution": "Reverted rollout and restored stable v4.5.3.",
    },
]

MOCK_SIMILAR_INCIDENTS_CACHE: List[Dict[str, Any]] = [
    {
        "incidentId": "INC-142",
        "incident_id": "INC-142",
        "similarity": 0.91,
        "outcome": "worked",
        "rootCause": "Redis cache TTL sync expiry under peak login spike",
        "root_cause": "Redis cache TTL sync expiry under peak login spike",
        "resolution": "Warmed cache from replica and applied jitter to TTL.",
    },
    {
        "incidentId": "INC-107",
        "incident_id": "INC-107",
        "similarity": 0.88,
        "outcome": "worked",
        "rootCause": "Hot product key cache expiration under promotional traffic",
        "root_cause": "Hot product key cache expiration under promotional traffic",
        "resolution": "Enabled request coalescing and pre-warmed cache.",
    },
]

# 12. Timeline Events
MOCK_TIMELINE_EVENTS: List[Dict[str, Any]] = [
    {
        "id": "EVT-001",
        "timestamp": "2026-09-29T11:30:00Z",
        "type": "system",
        "message": "Alert ingested from payments-db: Connection pool exhausted",
        "status": "triggered",
        "detail": "Latency P99: 3400ms, Error rate: 14%",
    },
    {
        "id": "EVT-002",
        "timestamp": "2026-09-29T11:30:04Z",
        "type": "agent",
        "message": "Classified incident severity as P1 based on user checkout impact",
        "status": "completed",
    },
    {
        "id": "EVT-003",
        "timestamp": "2026-09-29T11:30:12Z",
        "type": "memory",
        "message": "RECALL: Retrieved 3 similar historical incidents from Hindsight",
        "status": "completed",
        "detail": "Top match: INC-104 (94% similarity). Successful runbook: DB-POOL-RECOVERY.",
    },
    {
        "id": "EVT-004",
        "timestamp": "2026-09-29T11:30:25Z",
        "type": "agent",
        "message": "Generated root cause hypothesis & recommended runbook DB-POOL-RECOVERY",
        "status": "awaiting_approval",
        "detail": "Warning: Simple restart without pool expansion previously failed in INC-089.",
    },
]

# 1. Active Incidents & 3. P1/P2/P3 Incidents & 4. Database pool exhaustion
MOCK_ACTIVE_INCIDENT: Dict[str, Any] = {
    "id": "INC-2026-0929-01",
    "title": "PostgreSQL Connection Pool Saturation on Payments DB",
    "service": "payments-db",
    "severity": "P1",
    "status": "awaiting_approval",
    "symptoms": "HTTP 503 Service Unavailable spike, connection acquire timeout > 30s",
    "rootCause": "Connection pool capacity exhausted under sudden checkout surge",
    "root_cause": "Connection pool capacity exhausted under sudden checkout surge",
    "resolution": None,
    "startedAt": "2026-09-29T11:30:00Z",
    "started_at": "2026-09-29T11:30:00Z",
    "resolvedAt": None,
    "resolved_at": None,
    "affectedUsers": 4800,
    "affected_users": 4800,
    "recommendation": MOCK_RECOMMENDATION_DB_POOL,
    "similarIncidents": MOCK_SIMILAR_INCIDENTS,
    "similar_incidents": MOCK_SIMILAR_INCIDENTS,
    "timeline": MOCK_TIMELINE_EVENTS,
    "isNovel": False,
    "is_novel": False,
    "memoryUsed": True,
    "memory_used": True,
}

MOCK_P1_INCIDENT: Dict[str, Any] = MOCK_ACTIVE_INCIDENT

# 7. Cache stampede incident (P2, active)
MOCK_P2_INCIDENT: Dict[str, Any] = {
    "id": "INC-2026-0929-02",
    "title": "Redis Token Cache Stampede in Auth Cluster",
    "service": "auth-service",
    "severity": "P2",
    "status": "investigating",
    "symptoms": "Authentication latency P99 elevated to 4200ms, cache miss rate > 80%",
    "rootCause": "Redis token cache eviction causing stampede to backing database",
    "root_cause": "Redis token cache eviction causing stampede to backing database",
    "resolution": None,
    "startedAt": "2026-09-29T11:45:00Z",
    "started_at": "2026-09-29T11:45:00Z",
    "resolvedAt": None,
    "resolved_at": None,
    "affectedUsers": 2100,
    "affected_users": 2100,
    "recommendation": MOCK_RECOMMENDATION_CACHE,
    "similarIncidents": [
        {
            "incidentId": "INC-142",
            "similarity": 0.91,
            "outcome": "worked",
            "rootCause": "Redis cache TTL sync expiry under peak login spike",
            "resolution": "Warmed cache from replica and applied jitter to TTL.",
        }
    ],
    "timeline": [],
    "isNovel": False,
    "is_novel": False,
    "memoryUsed": True,
    "memory_used": True,
}

# 6. Bad deployment incident (P1, active)
MOCK_BAD_DEPLOY_INCIDENT: Dict[str, Any] = {
    "id": "INC-2026-0929-06",
    "title": "HTTP 502 Bad Gateway Spike on Web Gateway (Canary v3.2.1)",
    "service": "web-gateway",
    "severity": "P1",
    "status": "awaiting_approval",
    "symptoms": "Upstream connection reset, ingress error rate jumped to 28%",
    "rootCause": "Invalid TLS upstream routing config introduced in canary v3.2.1",
    "root_cause": "Invalid TLS upstream routing config introduced in canary v3.2.1",
    "resolution": None,
    "startedAt": "2026-09-29T11:50:00Z",
    "started_at": "2026-09-29T11:50:00Z",
    "resolvedAt": None,
    "resolved_at": None,
    "affectedUsers": 9200,
    "affected_users": 9200,
    "recommendation": MOCK_RECOMMENDATION_DEPLOY,
    "similarIncidents": [
        {
            "incidentId": "INC-062",
            "similarity": 0.95,
            "outcome": "worked",
            "rootCause": "Canary Envoy proxy TLS config regression",
            "resolution": "Rolled back to previous stable release via DEPLOY-ROLLBACK-PREV.",
        }
    ],
    "timeline": [],
    "isNovel": False,
    "is_novel": False,
    "memoryUsed": True,
    "memory_used": True,
}

# P3 Incident (Recommended)
MOCK_P3_INCIDENT: Dict[str, Any] = {
    "id": "INC-2026-0929-03",
    "title": "Slow Reporting Batch Query Execution",
    "service": "reporting-worker",
    "severity": "P3",
    "status": "recommended",
    "symptoms": "Nightly analytics export duration increased from 8m to 42m",
    "rootCause": "Missing index on reporting partition table following month-end rollover",
    "root_cause": "Missing index on reporting partition table following month-end rollover",
    "resolution": None,
    "startedAt": "2026-09-29T08:15:00Z",
    "started_at": "2026-09-29T08:15:00Z",
    "resolvedAt": None,
    "resolved_at": None,
    "affectedUsers": 120,
    "affected_users": 120,
    "recommendation": {
        "hypothesis": "Missing index on reporting partition table following month-end rollover",
        "confidence": 0.91,
        "evidence": ["Query plan indicates full table scan on raw_transactions_202609"],
        "recommendedSteps": ["Build partial index concurrently on transaction_timestamp"],
        "runbook": "INDEX-CONCURRENT-BUILD",
        "needsApproval": False,
        "isNovel": False,
    },
    "similarIncidents": [],
    "timeline": [],
    "isNovel": False,
    "memoryUsed": True,
    "memory_used": True,
}

# 2. Resolved Incidents & 5. Memory Leak & 8. Novel Incident
MOCK_RESOLVED_INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "INC-2026-0928-04",
        "title": "Kafka Consumer Partition Rebalance Deadlock",
        "service": "order-processor",
        "severity": "P1",
        "status": "resolved",
        "symptoms": "Order ingestion stopped, consumer group rebalance loops infinitely",
        "rootCause": "Partition revocation callback blocked on synchronous database write",
        "root_cause": "Partition revocation callback blocked on synchronous database write",
        "resolution": "Updated partition assignment callback to asynchronous dispatch and restarted pods.",
        "startedAt": "2026-09-28T18:15:00Z",
        "started_at": "2026-09-28T18:15:00Z",
        "resolvedAt": "2026-09-28T18:32:00Z",
        "resolved_at": "2026-09-28T18:32:00Z",
        "affectedUsers": 8400,
        "affected_users": 8400,
        "outcome": "worked",
        "isNovel": True,
        "is_novel": True,
        "memoryUsed": True,
        "memory_used": True,
    },
    {
        "id": "INC-2026-0927-05",
        "title": "JVM Heap Memory Leak in Catalog Cache",
        "service": "inventory-api",
        "severity": "P2",
        "status": "resolved",
        "symptoms": "Continuous Full GC pauses > 12s, OOMKilled container restarts",
        "rootCause": "Unbounded LRU cache retention in release v2.4.1",
        "root_cause": "Unbounded LRU cache retention in release v2.4.1",
        "resolution": "Rolled back deployment to v2.4.0 and pruned stale catalog cache references.",
        "startedAt": "2026-09-27T09:10:00Z",
        "started_at": "2026-09-27T09:10:00Z",
        "resolvedAt": "2026-09-27T09:24:00Z",
        "resolved_at": "2026-09-27T09:24:00Z",
        "affectedUsers": 3200,
        "affected_users": 3200,
        "outcome": "worked",
        "isNovel": False,
        "is_novel": False,
        "memoryUsed": True,
        "memory_used": True,
    },
]

MOCK_INCIDENTS: List[Dict[str, Any]] = [
    MOCK_ACTIVE_INCIDENT,
    MOCK_BAD_DEPLOY_INCIDENT,
    MOCK_P2_INCIDENT,
    MOCK_P3_INCIDENT,
    *MOCK_RESOLVED_INCIDENTS,
]

# All 5 Required Outage Scenarios
MOCK_SIMULATION_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "scenario-db-pool",
        "name": "Database Pool Exhaustion",
        "description": "Simulates sudden checkout request surge exhausting payments-db connections and timing out active checkouts.",
        "service": "payments-db",
        "expectedSeverity": "P1",
        "expected_severity": "P1",
        "symptoms": "connection pool exhausted, client requests timing out after 30s",
        "expectedMatchingIncident": "INC-104",
        "expected_matching_incident": "INC-104",
        "metrics": {"error_rate": 0.14, "latency_p99_ms": 3400, "affected_users": 4800},
    },
    {
        "id": "scenario-memory-leak",
        "name": "Memory Leak",
        "description": "Simulates uncollected JSON payloads in worker routine leading to progressive heap exhaustion and pod OOMKills.",
        "service": "order-processor",
        "expectedSeverity": "P1",
        "expected_severity": "P1",
        "symptoms": "OOMKilled pods restarting in order-processor deployment, memory > 95%",
        "expectedMatchingIncident": "INC-102",
        "expected_matching_incident": "INC-102",
        "metrics": {"restarts": 14, "memory_usage_pct": 98.4, "dropped_events": 680},
    },
    {
        "id": "scenario-bad-deployment",
        "name": "Bad Deployment",
        "description": "Simulates canary release introducing faulty upstream routing configuration resulting in immediate HTTP 502 spikes.",
        "service": "web-gateway",
        "expectedSeverity": "P1",
        "expected_severity": "P1",
        "symptoms": "HTTP 502 Bad Gateway rate > 25%, upstream connection resets",
        "expectedMatchingIncident": "INC-062",
        "expected_matching_incident": "INC-062",
        "metrics": {"error_rate": 0.28, "canary_traffic_pct": 20.0, "latency_p99_ms": 5200},
    },
    {
        "id": "scenario-cache-stampede",
        "name": "Cache Stampede",
        "description": "Simulates simultaneous cache key TTL expiration flooding primary PostgreSQL cluster with duplicate authentication queries.",
        "service": "auth-service",
        "expectedSeverity": "P2",
        "expected_severity": "P2",
        "symptoms": "cache miss rate > 80%, token validation latency 4200ms",
        "expectedMatchingIncident": "INC-142",
        "expected_matching_incident": "INC-142",
        "metrics": {"cache_miss_pct": 82.5, "db_cpu_pct": 94.0, "latency_p99_ms": 4200},
    },
    {
        "id": "scenario-novel-outage",
        "name": "Novel Incident",
        "description": "Simulates a first-time novel failure where external shipping gateway TLS handshake hangs indefinitely without read timeout.",
        "service": "shipping-gateway",
        "expectedSeverity": "P2",
        "expected_severity": "P2",
        "symptoms": "Upstream partner TLS handshake hanging indefinitely without TCP read timeout",
        "expectedMatchingIncident": "None (Novel Incident)",
        "expected_matching_incident": "None (Novel Incident)",
        "metrics": {"hung_threads": 48, "socket_errors": 190, "latency_p99_ms": 15000},
    },
]

MOCK_DEMO_ALERT: Dict[str, Any] = {
    "id": "ALT-DEMO-01",
    "service": "payments-db",
    "errorRate": 0.14,
    "error_rate": 0.14,
    "affectedUsers": 4800,
    "affected_users": 4800,
    "impact": "Critical checkout degradation for active shoppers",
    "timestamp": "2026-09-29T11:30:00Z",
    "message": "connection pool exhausted, requests timing out after 30s",
    "severity": "P1",
    "metrics": {
        "error_rate": 0.14,
        "latency_p99_ms": 3400,
        "affected_users": 4800,
    },
}


def generate_simulated_incident(scenario_id: str, memory_enabled: bool = True) -> Dict[str, Any]:
    """
    Synthesize realistic simulated incident based on selected scenario and memory state.
    Demonstrates full Hindsight recall when memory_enabled=True,
    or generic fallback LLM investigation when memory_enabled=False.
    """
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sc_str = str(scenario_id).lower()

    if "pool" in sc_str or "db" in sc_str:
        sim_id = "SIM-INC-DB-POOL"
        service = "payments-db"
        severity = "P1"
        title = "PostgreSQL Connection Pool Saturation on Payments DB"
        symptoms = "HTTP 503 Service Unavailable, connection acquire timeout > 30s"
        affected_users = 4800
        similar = MOCK_SIMILAR_INCIDENTS if memory_enabled else []
        is_novel = False
        if memory_enabled:
            rec = dict(MOCK_RECOMMENDATION_DB_POOL)
            root_cause = "Database connection pool saturation under high concurrent checkout volume"
        else:
            root_cause = "Generic database connection timeout (unverified without memory)"
            rec = {
                "hypothesis": "Generic database connection timeout (unverified without memory)",
                "confidence": 0.52,
                "evidence": [
                    "Raw telemetry: HTTP 503 error rate elevated to 14%",
                    "PostgreSQL connection wait queue length elevated",
                    "⚠️ Historical memory is OFF — no prior incidents or past post-mortems can be recalled.",
                ],
                "recommendedSteps": [
                    "Inspect payments-db active connection logs manually",
                    "Consider restarting application pods (⚠️ Warning: unverified risk)",
                    "Escalate to on-call DBA for exploratory diagnosis",
                ],
                "recommended_steps": [
                    "Inspect payments-db active connection logs manually",
                    "Consider restarting application pods (⚠️ Warning: unverified risk)",
                    "Escalate to on-call DBA for exploratory diagnosis",
                ],
                "runbook": "GENERIC-MANUAL-TRIAGE",
                "failedBefore": [],
                "failed_before": [],
                "previous_successful_fix": None,
                "previousSuccessfulFix": None,
                "needsApproval": True,
                "needs_approval": True,
                "isNovel": False,
                "is_novel": False,
            }

    elif "leak" in sc_str or "memory" in sc_str:
        sim_id = "SIM-INC-MEM-LEAK"
        service = "order-processor"
        severity = "P1"
        title = "Application Heap Memory Leak in Worker Routine"
        symptoms = "Continuous heap growth, memory usage > 95%, pod OOMKilled restarts every 30m"
        affected_users = 3600
        similar = MOCK_SIMILAR_INCIDENTS_MEMORY_LEAK if memory_enabled else []
        is_novel = False
        if memory_enabled:
            rec = dict(MOCK_RECOMMENDATION_MEMORY_LEAK)
            root_cause = "Unbounded in-memory LRU cache retention in worker routine causing progressive heap exhaustion"
        else:
            root_cause = "Container memory threshold exceeded (unverified without memory)"
            rec = {
                "hypothesis": "Container memory threshold exceeded (unverified without memory)",
                "confidence": 0.49,
                "evidence": [
                    "Raw telemetry: Pod memory utilization > 95%",
                    "Pod restart count elevated due to OOMKilled signal",
                    "⚠️ Historical memory is OFF — no prior incidents or past post-mortems can be recalled.",
                ],
                "recommendedSteps": [
                    "Inspect container memory metrics",
                    "Manually restart order-processor pods",
                    "Escalate to service owner for heap dump analysis",
                ],
                "recommended_steps": [
                    "Inspect container memory metrics",
                    "Manually restart order-processor pods",
                    "Escalate to service owner for heap dump analysis",
                ],
                "runbook": "GENERIC-MANUAL-TRIAGE",
                "failedBefore": [],
                "failed_before": [],
                "previous_successful_fix": None,
                "previousSuccessfulFix": None,
                "needsApproval": True,
                "needs_approval": True,
                "isNovel": False,
                "is_novel": False,
            }

    elif "deploy" in sc_str or "bad" in sc_str:
        sim_id = "SIM-INC-BAD-DEPLOY"
        service = "web-gateway"
        severity = "P1"
        title = "HTTP 502 Bad Gateway Spike on Web Gateway (Canary Regression)"
        symptoms = "HTTP 502 Bad Gateway rate > 25%, upstream connection resets"
        affected_users = 9200
        similar = MOCK_SIMILAR_INCIDENTS_DEPLOY if memory_enabled else []
        is_novel = False
        if memory_enabled:
            rec = dict(MOCK_RECOMMENDATION_DEPLOY)
            root_cause = "Faulty upstream routing configuration introduced in canary release v3.2.1"
        else:
            root_cause = "Upstream HTTP gateway error rate spike (unverified without memory)"
            rec = {
                "hypothesis": "Upstream HTTP gateway error rate spike (unverified without memory)",
                "confidence": 0.55,
                "evidence": [
                    "Raw telemetry: 502 Bad Gateway responses detected at ingress",
                    "Upstream connection resets logged in proxy metrics",
                    "⚠️ Historical memory is OFF — no prior incidents or past post-mortems can be recalled.",
                ],
                "recommendedSteps": [
                    "Check upstream service status",
                    "Consider rolling restart of web gateway",
                    "Escalate to networking team",
                ],
                "recommended_steps": [
                    "Check upstream service status",
                    "Consider rolling restart of web gateway",
                    "Escalate to networking team",
                ],
                "runbook": "GENERIC-MANUAL-TRIAGE",
                "failedBefore": [],
                "failed_before": [],
                "previous_successful_fix": None,
                "previousSuccessfulFix": None,
                "needsApproval": True,
                "needs_approval": True,
                "isNovel": False,
                "is_novel": False,
            }

    elif "cache" in sc_str or "stampede" in sc_str:
        sim_id = "SIM-INC-CACHE-STAMPEDE"
        service = "auth-service"
        severity = "P2"
        title = "Redis Token Cache Stampede in Auth Cluster"
        symptoms = "Cache miss rate > 80%, token validation latency spiked to 4200ms, DB CPU at 94%"
        affected_users = 2100
        similar = MOCK_SIMILAR_INCIDENTS_CACHE if memory_enabled else []
        is_novel = False
        if memory_enabled:
            rec = dict(MOCK_RECOMMENDATION_CACHE)
            root_cause = "Redis token cache key TTL eviction flooding primary database with duplicate queries"
        else:
            root_cause = "Elevated cache miss rate and authentication latency (unverified without memory)"
            rec = {
                "hypothesis": "Elevated cache miss rate and authentication latency (unverified without memory)",
                "confidence": 0.51,
                "evidence": [
                    "Raw telemetry: Cache miss rate metric > 80%",
                    "Database CPU utilization elevated to 94%",
                    "⚠️ Historical memory is OFF — no prior incidents or past post-mortems can be recalled.",
                ],
                "recommendedSteps": [
                    "Check Redis cluster connectivity",
                    "Monitor database query performance",
                    "Escalate to backend team",
                ],
                "recommended_steps": [
                    "Check Redis cluster connectivity",
                    "Monitor database query performance",
                    "Escalate to backend team",
                ],
                "runbook": "GENERIC-MANUAL-TRIAGE",
                "failedBefore": [],
                "failed_before": [],
                "previous_successful_fix": None,
                "previousSuccessfulFix": None,
                "needsApproval": True,
                "needs_approval": True,
                "isNovel": False,
                "is_novel": False,
            }

    else:  # Novel Incident
        sim_id = "SIM-INC-NOVEL-OUTAGE"
        service = "shipping-gateway"
        severity = "P2"
        title = "Upstream Third-Party Shipping Gateway TLS Handshake Hang"
        symptoms = "Partner TLS handshake hanging indefinitely without TCP read timeout, 48 hung threads"
        affected_users = 1450
        similar = []
        is_novel = True
        if memory_enabled:
            rec = dict(MOCK_RECOMMENDATION_NOVEL)
            root_cause = "Unprecedented upstream partner TLS handshake freeze without TCP read timeout (Novel Incident)"
        else:
            root_cause = "Generic connection hang on external partner endpoint (unverified without memory)"
            rec = {
                "hypothesis": "Generic connection hang on external partner endpoint (unverified without memory)",
                "confidence": 0.45,
                "evidence": [
                    "Raw telemetry: Outbound HTTP connection timeout metric elevated",
                    "Worker thread pool busy",
                    "⚠️ Historical memory is OFF — no prior incidents or past post-mortems can be recalled.",
                ],
                "recommendedSteps": [
                    "Inspect partner endpoint connectivity",
                    "Restart shipping-gateway pods",
                    "Contact third-party partner support",
                ],
                "recommended_steps": [
                    "Inspect partner endpoint connectivity",
                    "Restart shipping-gateway pods",
                    "Contact third-party partner support",
                ],
                "runbook": "GENERIC-MANUAL-TRIAGE",
                "failedBefore": [],
                "failed_before": [],
                "previous_successful_fix": None,
                "previousSuccessfulFix": None,
                "needsApproval": True,
                "needs_approval": True,
                "isNovel": False,
                "is_novel": False,
            }

    return {
        "id": sim_id,
        "title": title,
        "service": service,
        "severity": severity,
        "status": "investigating",
        "symptoms": symptoms,
        "rootCause": root_cause,
        "root_cause": root_cause,
        "resolution": None,
        "startedAt": now_str,
        "started_at": now_str,
        "resolvedAt": None,
        "resolved_at": None,
        "affectedUsers": affected_users,
        "affected_users": affected_users,
        "recommendation": rec,
        "similarIncidents": similar,
        "similar_incidents": similar,
        "timeline": MOCK_TIMELINE_EVENTS,
        "isNovel": is_novel,
        "is_novel": is_novel,
        "memoryUsed": memory_enabled,
        "memory_used": memory_enabled,
    }


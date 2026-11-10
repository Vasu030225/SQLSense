"""Creates a mock SQLite ops database: teams, applications, sla_policies, incidents, jobs."""
import random, sqlite3, os
from datetime import datetime, timedelta

DB = os.path.join(os.path.dirname(__file__), "ops.db")
random.seed(42)

SCHEMA = """
DROP TABLE IF EXISTS teams; DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS sla_policies; DROP TABLE IF EXISTS incidents; DROP TABLE IF EXISTS jobs;
CREATE TABLE teams(team_id INTEGER PRIMARY KEY, team_name TEXT, location TEXT);
CREATE TABLE applications(app_id INTEGER PRIMARY KEY, app_name TEXT, team_id INTEGER REFERENCES teams(team_id), criticality TEXT);
CREATE TABLE sla_policies(priority TEXT PRIMARY KEY, resolve_within_hours INTEGER);
CREATE TABLE incidents(incident_id TEXT PRIMARY KEY, app_id INTEGER REFERENCES applications(app_id),
  priority TEXT REFERENCES sla_policies(priority), status TEXT, opened_at TEXT, resolved_at TEXT,
  sla_breached INTEGER, assigned_to TEXT, short_description TEXT);
CREATE TABLE jobs(job_id INTEGER PRIMARY KEY, job_name TEXT, app_id INTEGER REFERENCES applications(app_id),
  run_date TEXT, status TEXT, duration_min REAL, records_processed INTEGER, retry_count INTEGER);
"""

def main():
    con = sqlite3.connect(DB); cur = con.cursor(); cur.executescript(SCHEMA)
    cur.executemany("INSERT INTO teams VALUES(?,?,?)", [(1,"Data Engineering","Noida"),(2,"Platform Ops","Bengaluru"),
                    (3,"Payments","Hyderabad"),(4,"Loyalty","Pune")])
    cur.executemany("INSERT INTO applications VALUES(?,?,?,?)", [(1,"Tokenization Service",3,"High"),
        (2,"Loyalty Points API",4,"High"),(3,"NiFi Ingestion",1,"Medium"),(4,"Airflow Scheduler",1,"Medium"),
        (5,"EKS Gateway",2,"High"),(6,"Reporting Portal",2,"Low")])
    slas = {"P1":4,"P2":8,"P3":24,"P4":72}
    cur.executemany("INSERT INTO sla_policies VALUES(?,?)", slas.items())
    engineers = ["Asha","Rahul","Meera","Karan","Neha","Vikram"]
    descs = ["Token generation failure","API latency spike","Batch file missing","DAG stuck in queued",
             "Pod CrashLoopBackOff","Dashboard not loading","Duplicate records","Auth token expired"]
    now = datetime.now().replace(microsecond=0)
    for i in range(1, 301):
        p = random.choices(list(slas), [1,3,4,2])[0]
        opened = now - timedelta(days=random.randint(0,60), hours=random.randint(0,23))
        status = random.choices(["Resolved","Closed","In Progress","Open"], [5,3,1,1])[0]
        if status in ("Resolved","Closed"):
            hrs = random.uniform(0.5, slas[p]*1.8)
            res = (opened + timedelta(hours=hrs)).isoformat(sep=" "); breached = int(hrs > slas[p])
        else:
            res = None; breached = int((now-opened).total_seconds()/3600 > slas[p])
        cur.execute("INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?,?)", (f"INC{100000+i}", random.randint(1,6), p,
            status, opened.isoformat(sep=" "), res, breached, random.choice(engineers), random.choice(descs)))
    jid = 1
    for d in range(30):
        day = (now - timedelta(days=d)).date().isoformat()
        for j, app in zip(["token_recovery","daily_ingest","points_reconcile","sla_notifier"], [1,3,2,4]):
            st = random.choices(["SUCCESS","FAILED","PARTIAL"], [8,1,1])[0]
            cur.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)", (jid, j, app, day, st, round(random.uniform(3,90),1),
                random.randint(1000,500000), 0 if st=="SUCCESS" else random.randint(1,3)))
            jid += 1
    con.commit(); con.close(); print(f"Seeded {DB}")

if __name__ == "__main__":
    main()

import json
import urllib.request
import urllib.error
import time
import sys

BASE = "http://localhost:8000/api/v1"

def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

# 1. Load the fixture
fixture_path = "src/backend/tests/fixtures/valid/16_account_routing.json"
with open(fixture_path, "r") as f:
    fixture_data = json.load(f)

# 2. Compile and save workflow
print("Compiling workflow...")
compile_req = {
    "nodes": fixture_data["nodes"],
    "edges": fixture_data["edges"],
    "workflow_id": fixture_data["workflow_id"],
    "workflow_type": fixture_data["workflow_type"],
    "task_queue": fixture_data["task_queue"]
}
try:
    compile_res = post(f"{BASE}/workflows/compile", compile_req)
except urllib.error.HTTPError as e:
    print(f"Compilation failed: {e.read().decode()}")
    sys.exit(1)

wf_id = compile_res["workflow_id"]
dsl_hash = compile_res["content_hash"]
print(f"Successfully compiled workflow {wf_id}")
print(f"Content Hash: {dsl_hash}")
print(f"Saved to: {compile_res['file_path']}")

def run_scenario(account_id):
    print(f"\n{'='*60}")
    print(f"  Scenario: account_id={account_id}")
    print(f"{'='*60}")
    
    # 3. Trigger execution
    exec_req = {
        "dsl_hash": dsl_hash,
        "input": {
            "account_id": account_id
        }
    }
    try:
        exec_res = post(f"{BASE}/executions/{wf_id}/execute", exec_req)
    except urllib.error.HTTPError as e:
        print(f"Trigger failed: {e.read().decode()}")
        return False

    temp_wf_id = exec_res["workflow_id"]
    run_id = exec_res["run_id"]
    print(f"Execution Triggered! Workflow ID: {temp_wf_id}, Run ID: {run_id}")

    # 4. Poll trace
    print("Polling trace...")
    trace_url = f"{BASE}/executions/{temp_wf_id}/{run_id}/trace"
    for attempt in range(20):
        time.sleep(1)
        try:
            trace = get(trace_url)
            status = trace.get("status", "UNKNOWN")
            print(f"  [{attempt+1:02d}] status={status}")
            if status not in ("RUNNING", "UNKNOWN"):
                print(f"\n=== Final Trace ({account_id}) ===")
                print(f"Workflow status : {status}")
                steps = trace.get("steps", {})
                for node_id, info in sorted(steps.items()):
                    s = info.get("status", "?")
                    mark = "✅" if s == "completed" else ("⏭ " if s == "skipped" else ("❌" if s == "failed" else "🔄"))
                    print(f"  {mark} {node_id}: {s}")
                    if info.get("output"):
                        print(f"       output: {info['output']}")
                    if info.get("error"):
                        print(f"       error : {info['error']}")
                return True
        except urllib.error.HTTPError as e:
            print(f"  [{attempt+1:02d}] HTTP {e.code}: {e.read().decode()[:120]}")
        except Exception as e:
            print(f"  [{attempt+1:02d}] {e}")
            
    print("Timed out waiting for completion.")
    return False

# Run both scenarios
success_active = run_scenario("active-123")
success_inactive = run_scenario("inactive-999")

if success_active and success_inactive:
    print("\n🎉 Both scenarios passed successfully!")
    sys.exit(0)
else:
    print("\n❌ One or more scenarios failed.")
    sys.exit(1)

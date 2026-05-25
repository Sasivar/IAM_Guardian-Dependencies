"""
IAM Guardian - FastAPI Backend
Run on EC2 master account: uvicorn main:app --host 0.0.0.0 --port 8000
"""

import boto3
import json
import uuid
import os
import time
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from agent.analyser import analyse_all_policies
from reports.pdf_generator import generate_pdf_report

load_dotenv()

app = FastAPI(title="IAM Guardian API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ─────────────────────────────────────────────────────────
MASTER_BUCKET = os.getenv("MASTER_BUCKET", "iam-guardian-master-bucket")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

ACCOUNTS = [
    {
        "account_id": "240939826956",
        "account_name": "Master Account",
        "is_master": True,
        "lambda_arn": None,
        "scan_role_arn": None,
    },
    {
        "account_id": "266889036314",
        "account_name": "Child Account 1",
        "is_master": False,
        "lambda_arn": "arn:aws:lambda:us-east-1:266889036314:function:IAMGuardianCollector",
        "scan_role_arn": "arn:aws:iam::266889036314:role/IAMGuardianScanRole",
    },
    {
        "account_id": "796761618689",
        "account_name": "Child Account 2",
        "is_master": False,
        "lambda_arn": "arn:aws:lambda:us-east-1:796761618689:function:IAMGuardianCollector",
        "scan_role_arn": "arn:aws:iam::796761618689:role/IAMGuardianScanRole",
    },
    {
        "account_id": "778685277916",
        "account_name": "Child Account 3",
        "is_master": False,
        "lambda_arn": "arn:aws:lambda:us-east-1:778685277916:function:IAMGuardianCollector",
        "scan_role_arn": "arn:aws:iam::778685277916:role/IAMGuardianScanRole",
    },
]

# In-memory scan store (use DB in production)
scans = {}


# ── Helper: assume role and get boto3 session ───────────────────────
def get_session_for_account(account: dict) -> boto3.Session:
    if account["is_master"]:
        return boto3.Session(region_name=AWS_REGION)

    sts = boto3.client("sts", region_name=AWS_REGION)
    response = sts.assume_role(
        RoleArn=account["scan_role_arn"],
        RoleSessionName=f"IAMGuardianMaster-{int(time.time())}",
    )
    creds = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=AWS_REGION,
    )


# ── Helper: invoke lambda in child account ──────────────────────────
def invoke_child_lambda(account: dict, scan_id: str):
    try:
        # Assume role in child account first
        session = get_session_for_account(account)
        lambda_client = session.client("lambda", region_name=AWS_REGION)

        payload = {
            "scan_id": scan_id,
            "master_bucket": MASTER_BUCKET,
        }

        response = lambda_client.invoke(
            FunctionName="IAMGuardianCollector",
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(payload),
        )
        print(f"Lambda invoked for account {account['account_id']}: {response['StatusCode']}")
        return True
    except Exception as e:
        print(f"Error invoking lambda for {account['account_id']}: {e}")
        scans[scan_id]["status"] = "error"
        scans[scan_id]["error"] = str(e)
        return False


# ── Helper: poll S3 for lambda results ─────────────────────────────
def wait_for_result_and_analyse(account: dict, scan_id: str):
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"scans/{account['account_id']}/{scan_id}.json"
    max_wait = 120  # 2 minutes max
    interval = 5
    elapsed = 0

    while elapsed < max_wait:
        try:
            obj = s3.get_object(Bucket=MASTER_BUCKET, Key=key)
            data = json.loads(obj["Body"].read().decode("utf-8"))
            print(f"Got {data['total_policies']} policies for scan {scan_id}")

            # Run AI analysis
            scans[scan_id]["status"] = "analysing"
            results = analyse_all_policies(data["policies"])

            # Build summary
            red = sum(1 for r in results if r["classification"] == "RED")
            amber = sum(1 for r in results if r["classification"] == "AMBER")
            green = sum(1 for r in results if r["classification"] == "GREEN")

            scans[scan_id].update({
                "status": "complete",
                "completed_at": datetime.utcnow().isoformat(),
                "total": len(results),
                "red": red,
                "amber": amber,
                "green": green,
                "policies": results,
            })
            return

        except s3.exceptions.NoSuchKey:
            time.sleep(interval)
            elapsed += interval
        except Exception as e:
            print(f"Analysis error: {e}")
            scans[scan_id]["status"] = "error"
            scans[scan_id]["error"] = str(e)
            return

    scans[scan_id]["status"] = "error"
    scans[scan_id]["error"] = "Timeout waiting for Lambda result"


# ── API Routes ──────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "IAM Guardian API is running"}


@app.get("/accounts")
def get_accounts():
    return [{"account_id": a["account_id"], "account_name": a["account_name"], "is_master": a["is_master"]} for a in ACCOUNTS]


@app.post("/scan/{account_id}")
def trigger_scan(account_id: str):
    account = next((a for a in ACCOUNTS if a["account_id"] == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    scan_id = str(uuid.uuid4())
    scans[scan_id] = {
        "scan_id": scan_id,
        "account_id": account_id,
        "account_name": account["account_name"],
        "status": "triggered",
        "triggered_at": datetime.utcnow().isoformat(),
        "total": 0,
        "red": 0,
        "amber": 0,
        "green": 0,
        "policies": [],
    }

    if account["is_master"]:
        # For master account, collect IAM directly without Lambda
        def scan_master():
            try:
                from collector.direct_collector import collect_master_account
                scans[scan_id]["status"] = "collecting"
                policies = collect_master_account()
                results = analyse_all_policies(policies)
                red = sum(1 for r in results if r["classification"] == "RED")
                amber = sum(1 for r in results if r["classification"] == "AMBER")
                green = sum(1 for r in results if r["classification"] == "GREEN")
                scans[scan_id].update({
                    "status": "complete",
                    "completed_at": datetime.utcnow().isoformat(),
                    "total": len(results),
                    "red": red, "amber": amber, "green": green,
                    "policies": results,
                })
            except Exception as e:
                scans[scan_id]["status"] = "error"
                scans[scan_id]["error"] = str(e)

        threading.Thread(target=scan_master, daemon=True).start()
    else:
        # For child accounts, invoke Lambda then wait for S3 result
        success = invoke_child_lambda(account, scan_id)
        if success:
            scans[scan_id]["status"] = "collecting"
            thread = threading.Thread(
                target=wait_for_result_and_analyse,
                args=(account, scan_id),
                daemon=True,
            )
            thread.start()

    return {"scan_id": scan_id, "status": scans[scan_id]["status"]}


@app.get("/scan/{scan_id}")
def get_scan_result(scan_id: str):
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scans[scan_id]


@app.get("/scan/{scan_id}/report")
def download_report(scan_id: str):
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scans[scan_id]["status"] != "complete":
        raise HTTPException(status_code=400, detail="Scan not complete yet")

    pdf_path = generate_pdf_report(scans[scan_id], scan_id)
    return FileResponse(
        path=pdf_path,
        filename=f"iam-guardian-report-{scan_id[:8]}.pdf",
        media_type="application/pdf",
    )


@app.get("/scans")
def list_all_scans():
    return [
        {
            "scan_id": s["scan_id"],
            "account_id": s["account_id"],
            "account_name": s["account_name"],
            "status": s["status"],
            "triggered_at": s.get("triggered_at"),
            "total": s.get("total", 0),
            "red": s.get("red", 0),
            "amber": s.get("amber", 0),
            "green": s.get("green", 0),
        }
        for s in scans.values()
    ]

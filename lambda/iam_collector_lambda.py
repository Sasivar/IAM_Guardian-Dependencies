"""
IAM Guardian - Lambda Function
Deploy this on each child account (Child 1, Child 2, Child 3)
This lambda collects all IAM policies and uploads to master S3 bucket
"""

import boto3
import json
import os
from datetime import datetime, timezone


def lambda_handler(event, context):
    print(f"IAM Guardian Lambda triggered: {json.dumps(event)}")

    account_id = boto3.client("sts").get_caller_identity()["Account"]
    scan_id = event.get("scan_id", f"scan-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    master_bucket = event.get("master_bucket", "iam-guardian-master-bucket")

    try:
        iam = boto3.client("iam")
        policies = []

        # ── Collect IAM Roles ──────────────────────────────────────────
        paginator = iam.get_paginator("list_roles")
        for page in paginator.paginate():
            for role in page["Roles"]:
                role_name = role["RoleName"]

                # Get last used date
                try:
                    role_detail = iam.get_role(RoleName=role_name)["Role"]
                    last_used_info = role_detail.get("RoleLastUsed", {})
                    last_used_date = last_used_info.get("LastUsedDate", None)
                    if last_used_date:
                        days_ago = (datetime.now(timezone.utc) - last_used_date).days
                    else:
                        days_ago = 9999  # Never used
                except Exception:
                    days_ago = 9999

                # Inline policies on role
                try:
                    inline_policies = iam.list_role_policies(RoleName=role_name)["PolicyNames"]
                    for policy_name in inline_policies:
                        doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                        policies.append({
                            "type": "inline",
                            "attached_to": "role",
                            "entity_name": role_name,
                            "policy_name": policy_name,
                            "last_used_days_ago": days_ago,
                            "arn": role.get("Arn", ""),
                            "document": doc["PolicyDocument"],
                        })
                except Exception as e:
                    print(f"Error getting inline policies for {role_name}: {e}")

                # Managed policies attached to role
                try:
                    managed = iam.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]
                    for policy in managed:
                        try:
                            version_id = iam.get_policy(PolicyArn=policy["PolicyArn"])["Policy"]["DefaultVersionId"]
                            doc = iam.get_policy_version(PolicyArn=policy["PolicyArn"], VersionId=version_id)
                            policies.append({
                                "type": "managed",
                                "attached_to": "role",
                                "entity_name": role_name,
                                "policy_name": policy["PolicyName"],
                                "policy_arn": policy["PolicyArn"],
                                "last_used_days_ago": days_ago,
                                "arn": role.get("Arn", ""),
                                "document": doc["PolicyVersion"]["Document"],
                            })
                        except Exception as e:
                            print(f"Error getting managed policy {policy['PolicyName']}: {e}")
                except Exception as e:
                    print(f"Error listing managed policies for {role_name}: {e}")

        # ── Collect IAM Users ──────────────────────────────────────────
        user_paginator = iam.get_paginator("list_users")
        for page in user_paginator.paginate():
            for user in page["Users"]:
                user_name = user["UserName"]

                # Inline policies on user
                try:
                    inline_policies = iam.list_user_policies(UserName=user_name)["PolicyNames"]
                    for policy_name in inline_policies:
                        doc = iam.get_user_policy(UserName=user_name, PolicyName=policy_name)
                        policies.append({
                            "type": "inline",
                            "attached_to": "user",
                            "entity_name": user_name,
                            "policy_name": policy_name,
                            "last_used_days_ago": 0,
                            "arn": user.get("Arn", ""),
                            "document": doc["PolicyDocument"],
                        })
                except Exception as e:
                    print(f"Error getting inline policies for user {user_name}: {e}")

                # Managed policies on user
                try:
                    managed = iam.list_attached_user_policies(UserName=user_name)["AttachedPolicies"]
                    for policy in managed:
                        try:
                            version_id = iam.get_policy(PolicyArn=policy["PolicyArn"])["Policy"]["DefaultVersionId"]
                            doc = iam.get_policy_version(PolicyArn=policy["PolicyArn"], VersionId=version_id)
                            policies.append({
                                "type": "managed",
                                "attached_to": "user",
                                "entity_name": user_name,
                                "policy_name": policy["PolicyName"],
                                "policy_arn": policy["PolicyArn"],
                                "last_used_days_ago": 0,
                                "arn": user.get("Arn", ""),
                                "document": doc["PolicyVersion"]["Document"],
                            })
                        except Exception as e:
                            print(f"Error getting managed policy for user {user_name}: {e}")
                except Exception as e:
                    print(f"Error listing managed policies for user {user_name}: {e}")

        # ── Upload to Master S3 ────────────────────────────────────────
        payload = {
            "account_id": account_id,
            "scan_id": scan_id,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "total_policies": len(policies),
            "policies": policies,
        }

        s3 = boto3.client("s3")
        key = f"scans/{account_id}/{scan_id}.json"
        s3.put_object(
            Bucket=master_bucket,
            Key=key,
            Body=json.dumps(payload, default=str),
            ContentType="application/json",
        )

        print(f"✅ Uploaded {len(policies)} policies to s3://{master_bucket}/{key}")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "account_id": account_id,
                "scan_id": scan_id,
                "total_policies": len(policies),
                "s3_key": key,
            }),
        }

    except Exception as e:
        print(f"❌ Lambda error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": str(e)}),
        }

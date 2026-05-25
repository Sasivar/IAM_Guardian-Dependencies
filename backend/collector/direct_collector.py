"""
IAM Guardian - Direct Collector for Master Account
Used when scanning the master account directly (no Lambda needed)
"""

import boto3
from datetime import datetime, timezone


def collect_master_account():
    iam = boto3.client("iam")
    policies = []

    # Collect Roles
    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            role_name = role["RoleName"]

            try:
                role_detail = iam.get_role(RoleName=role_name)["Role"]
                last_used_info = role_detail.get("RoleLastUsed", {})
                last_used_date = last_used_info.get("LastUsedDate", None)
                days_ago = (datetime.now(timezone.utc) - last_used_date).days if last_used_date else 9999
            except Exception:
                days_ago = 9999

            # Inline policies
            try:
                for policy_name in iam.list_role_policies(RoleName=role_name)["PolicyNames"]:
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
            except Exception:
                pass

            # Managed policies
            try:
                for policy in iam.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]:
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
                    except Exception:
                        pass
            except Exception:
                pass

    # Collect Users
    user_paginator = iam.get_paginator("list_users")
    for page in user_paginator.paginate():
        for user in page["Users"]:
            user_name = user["UserName"]

            try:
                for policy_name in iam.list_user_policies(UserName=user_name)["PolicyNames"]:
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
            except Exception:
                pass

            try:
                for policy in iam.list_attached_user_policies(UserName=user_name)["AttachedPolicies"]:
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
                    except Exception:
                        pass
            except Exception:
                pass

    return policies

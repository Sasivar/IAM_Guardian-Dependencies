# Child IAM Policy

## Lambda Function - **IAMGuardianCollector**

- Configuration → Permission → Resource-Based Policy —— AllowMasterAccountInvoke

```
{
  "Version": "2012-10-17",
  "Id": "default",
  "Statement": [
    {
      "Sid": "AllowMasterAccountInvoke",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::240939826956:role/IAMGuardianEC2Role"
      },
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:796761618689:function:IAMGuardianCollector"
    }
  ]
}
```

!image.png

- Configuration → Permission → Create new execution role —— **IAMGuardianCollector-role-3h1tnig2**
    - Create inline policy
    
    ```
    {
    	"Version": "2012-10-17",
    	"Statement": [
    		{
    			"Effect": "Allow",
    			"Action": [
    				"iam:ListRoles",
    				"iam:ListUsers",
    				"iam:ListGroups",
    				"iam:ListPolicies",
    				"iam:ListRolePolicies",
    				"iam:ListUserPolicies",
    				"iam:ListGroupPolicies",
    				"iam:ListAttachedRolePolicies",
    				"iam:ListAttachedUserPolicies",
    				"iam:ListAttachedGroupPolicies",
    				"iam:GetRole",
    				"iam:GetUser",
    				"iam:GetPolicy",
    				"iam:GetPolicyVersion",
    				"iam:GetRolePolicy",
    				"iam:GetUserPolicy"
    			],
    			"Resource": "*"
    		},
    		{
    			"Effect": "Allow",
    			"Action": [
    				"s3:PutObject",
    				"s3:PutObjectAcl"
    			],
    			"Resource": "arn:aws:s3:::iam-guardian-master-bucket/*"
    		}
    	]
    }
    ```
    
    - Add AWS managed policy → AWSLambdaBasicExecutionRole

## Create IAM Role → **IAMGuardianScanRole**

- Create Inline policy → IAMGuardianScanPolicy

```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "ReadIAMPolicies",
			"Effect": "Allow",
			"Action": [
				"iam:ListRoles",
				"iam:ListUsers",
				"iam:ListGroups",
				"iam:ListPolicies",
				"iam:ListRolePolicies",
				"iam:ListUserPolicies",
				"iam:ListGroupPolicies",
				"iam:ListAttachedRolePolicies",
				"iam:ListAttachedUserPolicies",
				"iam:ListAttachedGroupPolicies",
				"iam:GetRole",
				"iam:GetUser",
				"iam:GetPolicy",
				"iam:GetPolicyVersion",
				"iam:GetRolePolicy",
				"iam:GetUserPolicy"
			],
			"Resource": "*"
		},
		{
			"Sid": "SendToMasterS3",
			"Effect": "Allow",
			"Action": [
				"s3:PutObject",
				"s3:PutObjectAcl"
			],
			"Resource": "arn:aws:s3:::iam-guardian-master-bucket/*"
		},
		{
			"Sid": "CreateDemoRoles",
			"Effect": "Allow",
			"Action": [
				"s3:PutObject",
				"s3:PutObjectAcl",
				"iam:CreateRole",
				"iam:DeleteRole",
				"iam:PutRolePolicy",
				"iam:DeleteRolePolicy",
				"iam:TagRole"
			],
			"Resource": "arn:aws:iam::*:role/Demo-*"
		},
		{
			"Sid": "AllowInvokeCollectorAnyAccount",
			"Effect": "Allow",
			"Action": "lambda:InvokeFunction",
			"Resource": "arn:aws:lambda:*:*:function:IAMGuardianCollector*"
		}
	]
}

```

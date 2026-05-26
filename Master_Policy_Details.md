# Master IAM Policy

# Policy 1: AssumeChildRoles

```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": "sts:AssumeRole",
			"Resource": [
				"arn:aws:iam::266889036314:role/IAMGuardianScanRole",
				"arn:aws:iam::796761618689:role/IAMGuardianScanRole",
				"arn:aws:iam::778685277916:role/IAMGuardianScanRole"
			]
		}
	]
}
```

# Policy 2: MasterS3Access

```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": [
				"s3:GetObject",
				"s3:PutObject",
				"s3:ListBucket",
				"s3:DeleteObject"
			],
			"Resource": [
				"arn:aws:s3:::iam-guardian-master-bucket",
				"arn:aws:s3:::iam-guardian-master-bucket/*"
			]
		},
		{
			"Sid": "BedrockAccess",
			"Effect": "Allow",
			"Action": [
				"bedrock:InvokeModel",
				"bedrock:InvokeModelWithResponseStream"
			],
			"Resource": "*"
		}
	]
}
```

# Policy 3: InvokeLambda

```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": "lambda:InvokeFunction",
			"Resource": [
				"arn:aws:lambda:us-east-1:266889036314:function:IAMGuardianCollector",
				"arn:aws:lambda:us-east-1:796761618689:function:IAMGuardianCollector",
				"arn:aws:lambda:us-east-1:778685277916:function:IAMGuardianCollector"
			]
		}
	]
}
```

# Policy 4: ReadOwnIAM

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
		}
	]
}
```

# S3 Bucket Policy - **iam-guardian-master-bucket**

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowChildAccountWrite",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::778685277916:role/IAMGuardianScanRole",
                    "arn:aws:iam::796761618689:role/IAMGuardianCollector-role-3h1tnig2",
                    "arn:aws:iam::796761618689:role/IAMGuardianScanRole",
                    "arn:aws:iam::266889036314:role/IAMGuardianScanRole"
                ]
            },
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::iam-guardian-master-bucket/*"
        }
    ]
}
```


# AWS 서비스 데이터 수집 항목 및 형식

이 문서는 AWS 서비스(IAM, EC2, RDS, Lambda, S3)에서 수집되는 데이터 항목과 실제 데이터 형식을 정리한 것입니다.

## 1. IAM (Identity and Access Management)

```python
{
    'users': [
        {
            'name': 'string',  # 사용자 이름
            'user_id': 'AIDA123456789EXAMPLE',
            'arn': 'arn:aws:iam::123456789012:user/admin',
            'create_date': '2023-01-15T09:12:32Z',
            'password_last_used': '2023-05-20T14:25:43Z',
            'access_keys': [
                {
                    'access_key_id': 'AKIA123456789EXAMPLE',
                    'status': 'Active',
                    'create_date': '2023-01-15T09:15:20Z',
                    'last_used': {
                        'date': '2023-05-20T14:25:43Z',
                        'region': 'ap-northeast-2',
                        'service_name': 'ec2'
                    }
                }
            ],
            'mfa_devices': [
                {
                    'serial_number': 'arn:aws:iam::123456789012:mfa/admin',
                    'enable_date': '2023-01-15T09:20:15Z'
                }
            ],
            'groups': ['Administrators', 'Developers'],
            'attached_policies': [
                {
                    'policy_name': 'AdministratorAccess',
                    'policy_arn': 'arn:aws:iam::aws:policy/AdministratorAccess'
                }
            ]
        },
        {
            'name': 'developer',
            'user_id': 'AIDA98765432EXAMPLE',
            'arn': 'arn:aws:iam::123456789012:user/developer',
            'create_date': '2023-02-10T11:32:45Z',
            'password_last_used': '2023-05-19T10:15:22Z',
            'access_keys': [
                {
                    'access_key_id': 'AKIA98765432EXAMPLE',
                    'status': 'Active',
                    'create_date': '2023-02-10T11:35:12Z',
                    'last_used': {
                        'date': '2023-05-19T10:15:22Z',
                        'region': 'ap-northeast-2',
                        'service_name': 's3'
                    }
                }
            ],
            'mfa_devices': [],
            'groups': ['Developers'],
            'attached_policies': [
                {
                    'policy_name': 'PowerUserAccess',
                    'policy_arn': 'arn:aws:iam::aws:policy/PowerUserAccess'
                }
            ]
        }
    ],
    'root_account': {
        'mfa_active': True,
        'access_keys_present': False,
        'last_used': '2023-01-10T08:45:30Z'
    },
    'password_policy': {
        'minimum_password_length': 12,
        'require_symbols': True,
        'require_numbers': True,
        'require_uppercase_characters': True,
        'require_lowercase_characters': True,
        'allow_users_to_change_password': True,
        'expire_passwords': True,
        'max_password_age': 90,
        'password_reuse_prevention': 24
    },
    'roles': [
        {
            'role_name': 'lambda-execution-role',
            'role_id': 'AROA123456789EXAMPLE',
            'arn': 'arn:aws:iam::123456789012:role/lambda-execution-role',
            'create_date': '2023-03-05T14:22:10Z',
            'assume_role_policy_document': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {
                            'Service': 'lambda.amazonaws.com'
                        },
                        'Action': 'sts:AssumeRole'
                    }
                ]
            },
            'attached_policies': [
                {
                    'policy_name': 'AWSLambdaBasicExecutionRole',
                    'policy_arn': 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                }
            ]
        }
    ],
    'policies': [
        {
            'policy_name': 'S3ReadOnlyAccess',
            'policy_id': 'ANPA123456789EXAMPLE',
            'arn': 'arn:aws:iam::123456789012:policy/S3ReadOnlyAccess',
            'create_date': '2023-04-12T09:45:30Z',
            'update_date': '2023-04-12T09:45:30Z',
            'attachment_count': 5,
            'default_version_id': 'v1'
        }
    ]
}
```

## 2. EC2 (Elastic Compute Cloud) ok

```python
{
  "instances": [
    {
      "id": "i-0758f1823d43bfada",
      "type": "t3.medium",
      "state": "running",
      "az": "ap-northeast-2a",
      "launch_time": "2025-01-23 14:01:48+00:00",
      "state_transition_time": null,
      "security_groups": [
        {
          "group_id": "sg-0c4157b772abea871",
          "ip_ranges": ["0.0.0.0/0"],
          "ports": [80]
        }
      ],
      "tags": [
        {
          "Key": "Name",
          "Value": "nonono"
        }
      ],
      "cpu_metrics": [23.49, ...],
      "cpu_analysis": {
        "low_usage_days": 0,
        "high_usage_days": 0
      },
      "network_metrics": {
        "NetworkIn": 228.4,
        "NetworkOut": 0.0,
        "NetworkPacketsIn": 3.2,
        "NetworkPacketsOut": 0.0
      },
      "volumes": [
        {
          "Attachments": [
            {
              "AttachTime": "2025-01-23 14:01:49+00:00",
              "Device": "/dev/xvda",
              "InstanceId": "i-0758f1823d43bfada",
              "State": "attached",
              "VolumeId": "vol-02a19f5a27c7ddfa4",
              "DeleteOnTermination": true
            }
          ],
          "AvailabilityZone": "ap-northeast-2a",
          "CreateTime": "2025-01-23 14:01:49.124000+00:00",
          "Encrypted": false,
          "Size": 50,
          "SnapshotId": "snap-06eebab18521298ac",
          "State": "in-use",
          "VolumeId": "vol-02a19f5a27c7ddfa4",
          "Iops": 3000,
          "VolumeType": "gp3",
          "MultiAttachEnabled": false,
          "Throughput": 125
        }
      ]
    },
    ...
  ]
}
```

## 3. RDS (Relational Database Service)

```python
{
    'instances': [
        {
            'identifier': 'production-db',
            'engine': 'mysql',
            'engine_version': '8.0.28',
            'instance_class': 'db.t3.large',
            'status': 'available',
            'storage_type': 'gp2',
            'allocated_storage': 100,
            'multi_az': True,
            'creation_time': '2023-02-15T10:30:45Z',
            'backup_retention_period': 7,
            'master_username': 'admin',
            'publicly_accessible': False,
            'vpc_id': 'vpc-0abc123def456789',
            'subnet_group': 'default-vpc-0abc123def456789',
            'endpoint': 'production-db.abcdef123456.ap-northeast-2.rds.amazonaws.com',
            'port': 3306,
            'security_groups': [
                {
                    'id': 'sg-0abc123def456789',
                    'status': 'active'
                }
            ],
            'parameters': {
                'max_connections': 1000,
                'innodb_buffer_pool_size': '4294967296',
                'character_set_server': 'utf8mb4',
                'collation_server': 'utf8mb4_unicode_ci'
            },
            'metrics': {
                'cpu_utilization': 35.7,
                'free_memory': 2048.5,
                'read_iops': 120.3,
                'write_iops': 85.6,
                'read_latency': 0.8,
                'write_latency': 1.2,
                'database_connections': 42,
                'freeable_memory': 4096.2,
                'free_storage_space': 52428.8
            },
            'tags': {
                'Environment': 'Production',
                'Project': 'E-commerce',
                'ManagedBy': 'DevOps'
            }
        },
        {
            'identifier': 'staging-db',
            'engine': 'postgres',
            'engine_version': '14.3',
            'instance_class': 'db.t3.medium',
            'status': 'available',
            'storage_type': 'gp2',
            'allocated_storage': 50,
            'multi_az': False,
            'creation_time': '2023-03-20T14:15:30Z',
            'backup_retention_period': 3,
            'master_username': 'postgres',
            'publicly_accessible': False,
            'vpc_id': 'vpc-0abc123def456789',
            'subnet_group': 'default-vpc-0abc123def456789',
            'endpoint': 'staging-db.abcdef123456.ap-northeast-2.rds.amazonaws.com',
            'port': 5432,
            'security_groups': [
                {
                    'id': 'sg-0def456789abc123',
                    'status': 'active'
                }
            ],
            'parameters': {
                'max_connections': 500,
                'shared_buffers': '1GB',
                'work_mem': '64MB',
                'maintenance_work_mem': '256MB'
            },
            'metrics': {
                'cpu_utilization': 15.2,
                'free_memory': 1536.8,
                'read_iops': 45.6,
                'write_iops': 32.1,
                'read_latency': 0.5,
                'write_latency': 0.9,
                'database_connections': 12,
                'freeable_memory': 2048.5,
                'free_storage_space': 35840.0
            },
            'tags': {
                'Environment': 'Staging',
                'Project': 'E-commerce',
                'ManagedBy': 'DevOps'
            }
        }
    ]
}
```

## 4. Lambda

```python
{
  "functions": [
    {
      "FunctionName": "silver-crawling",
      "FunctionArn": "arn:aws:lambda:ap-northeast-2:713881821833:function:silver-crawling",
      "Runtime": "python3.12",
      "MemorySize": 128,
      "Timeout": 60,
      "CodeSize": 2715,
      "LastModified": "2025-01-12T04:43:58.000+0000",
      "Handler": "lambda_function.lambda_handler",
      "Environment": {},
      "TracingConfig": "PassThrough",
      "Architectures": ["x86_64"],
      "Tags": {},
      "ReservedConcurrency": null,
      "DeadLetterConfig": {},
      "Layers": [
        {
          "Arn": "arn:aws:lambda:ap-northeast-2:770693421928:layer:Klayers-p312-beautifulsoup4:3",
          "CodeSize": 116796
        }
      ],
      "VersionsInfo": [
        {
          "Version": "$LATEST"
        }
      ],
      "UrlConfig": null,
      "VpcConfig": {},
      "DebugLogsDetected": false
    }
  ]
}
```

## 5. S3 (Simple Storage Service)

```python
{
  "buckets": [
    {
      "name": "article-to-shorts",
      "creation_date": "2025-05-21 12:47:25+00:00",
      "region": "ap-northeast-2",
      "public_access": false,
      "versioning": false,
      "encryption": true,
      "lifecycle_rules": [],
      "tags": {
        "aws:cloudformation:stack-name": "ShortFormVideoStack"
      },
      "size": 0,
      "object_count": 0
    }
  ]
}
```
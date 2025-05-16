import boto3
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, List, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_iam_data(aws_access_key: str, aws_secret_key: str, region: str, collection_id: str = None) -> Dict:
    """IAM 데이터 수집"""
    log_prefix = f"[{collection_id}] " if collection_id else ""
    logger.info(f"{log_prefix}Starting IAM data collection")
    try:
        iam_client = boto3.client(
            'iam',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        result = {
            'users': [],
            'root_account': {},
            'password_policy': {},
            'roles': [],
            'policies': []
        }
        
        # 1. 사용자 정보 수집
        logger.info(f"{log_prefix}Collecting IAM users data")
        response = iam_client.list_users()
        for user in response['Users']:
            # 사용자 상세 정보 수집
            user_info = {
                'name': user['UserName'],
                'created': user['CreateDate'].strftime('%Y-%m-%d'),
                'id': user['UserId'],
                'mfa_enabled': False,
                'access_keys': [],
                'password_enabled': False,
                'groups': [],
                'policies': [],
                'last_activity': None
            }
            
            # MFA 디바이스 확인
            try:
                mfa_devices = iam_client.list_mfa_devices(UserName=user['UserName'])
                user_info['mfa_enabled'] = len(mfa_devices['MFADevices']) > 0
            except Exception as e:
                logger.error(f"{log_prefix}Error checking MFA for {user['UserName']}: {str(e)}")

            # 액세스 키 정보 수집
            try:
                access_keys = iam_client.list_access_keys(UserName=user['UserName'])
                current_time = datetime.now(timezone.utc)
                
                for key in access_keys['AccessKeyMetadata']:
                    last_used = None
                    try:
                        key_last_used = iam_client.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
                        if 'LastUsedDate' in key_last_used.get('AccessKeyLastUsed', {}):
                            last_used = key_last_used['AccessKeyLastUsed']['LastUsedDate']
                    except Exception as e:
                        logger.error(f"{log_prefix}Error getting key last used for {key['AccessKeyId']}: {str(e)}")
                    
                    # 키 생성 후 경과 일수 계산
                    days_since_created = (current_time - key['CreateDate']).days
                    
                    # 마지막 사용 후 경과 일수 계산
                    days_since_used = None
                    if last_used:
                        days_since_used = (current_time - last_used).days
                    
                    key_info = {
                        'id': key['AccessKeyId'],
                        'created': key['CreateDate'].strftime('%Y-%m-%d'),
                        'status': key['Status'],
                        'last_used': last_used.strftime('%Y-%m-%d') if last_used else None,
                        'days_since_created': days_since_created,
                        'days_since_used': days_since_used
                    }
                    
                    user_info['access_keys'].append(key_info)
                    
                    # 사용자 마지막 활동 업데이트
                    if last_used and (user_info['last_activity'] is None or last_used > user_info['last_activity']):
                        user_info['last_activity'] = last_used
            except Exception as e:
                logger.error(f"{log_prefix}Error collecting access keys for {user['UserName']}: {str(e)}")

            # 로그인 프로필 확인 (콘솔 액세스)
            try:
                login_profile = iam_client.get_login_profile(UserName=user['UserName'])
                user_info['password_enabled'] = True
                user_info['password_created'] = login_profile['LoginProfile'].get('CreateDate')
                
                # 비밀번호 마지막 사용 시간 확인
                try:
                    # 자격 증명 보고서 가져오기 시도
                    try:
                        credential_report = iam_client.get_credential_report()
                    except iam_client.exceptions.CredentialReportNotPresentException:
                        # 보고서가 없으면 생성 요청
                        logger.info(f"{log_prefix}Credential report not found, generating new report")
                        iam_client.generate_credential_report()
                        
                        # 보고서 생성 완료 대기
                        import time
                        for _ in range(10):  # 최대 10번 시도
                            try:
                                report_state = iam_client.generate_credential_report()['State']
                                if report_state == 'COMPLETE':
                                    credential_report = iam_client.get_credential_report()
                                    break
                                time.sleep(2)  # 2초 대기
                            except Exception:
                                time.sleep(2)
                                continue
                    
                    # 보고서 처리
                    if 'Content' in credential_report:
                        import csv
                        from io import StringIO
                        
                        report = csv.DictReader(StringIO(credential_report['Content'].decode('utf-8')))
                        for row in report:
                            if row['user'] == user['UserName']:
                                if row['password_last_used'] != 'N/A':
                                    try:
                                        # 여러 가능한 형식 시도
                                        formats = ['%Y-%m-%dT%H:%M:%S+00:00', '%Y-%m-%dT%H:%M:%SZ']
                                        for fmt in formats:
                                            try:
                                                password_last_used = datetime.strptime(row['password_last_used'], fmt)
                                                # 타임존 정보 추가
                                                password_last_used = password_last_used.replace(tzinfo=timezone.utc)
                                                user_info['password_last_used'] = password_last_used.strftime('%Y-%m-%d')
                                                break
                                            except ValueError:
                                                continue
                                    except Exception as e:
                                        logger.warning(f"{log_prefix}Could not parse date: {row['password_last_used']}, error: {str(e)}")
                                    
                                    # 사용자 마지막 활동 업데이트
                                    if 'password_last_used' in user_info and password_last_used:
                                        # 타임존 정보 추가
                                        if password_last_used.tzinfo is None:
                                            password_last_used = password_last_used.replace(tzinfo=timezone.utc)
                                        
                                        if user_info['last_activity'] is None:
                                            user_info['last_activity'] = password_last_used
                                        elif user_info['last_activity'].tzinfo is None:
                                            # last_activity에 타임존 정보 추가
                                            user_info['last_activity'] = user_info['last_activity'].replace(tzinfo=timezone.utc)
                                            if password_last_used > user_info['last_activity']:
                                                user_info['last_activity'] = password_last_used
                                        elif password_last_used > user_info['last_activity']:
                                            user_info['last_activity'] = password_last_used
                                break
                except Exception as e:
                    logger.error(f"{log_prefix}Error getting credential report: {str(e)}")
                    
            except iam_client.exceptions.NoSuchEntityException:
                user_info['password_enabled'] = False
            except Exception as e:
                logger.error(f"{log_prefix}Error checking login profile for {user['UserName']}: {str(e)}")

            # 그룹 멤버십 확인
            try:
                groups = iam_client.list_groups_for_user(UserName=user['UserName'])
                user_info['groups'] = [g['GroupName'] for g in groups['Groups']]
            except Exception as e:
                logger.error(f"{log_prefix}Error getting groups for {user['UserName']}: {str(e)}")

            # 직접 연결된 정책 확인
            try:
                attached_policies = iam_client.list_attached_user_policies(UserName=user['UserName'])
                user_policies = []
                
                for policy in attached_policies['AttachedPolicies']:
                    policy_detail = iam_client.get_policy(PolicyArn=policy['PolicyArn'])
                    policy_version = iam_client.get_policy_version(
                        PolicyArn=policy['PolicyArn'],
                        VersionId=policy_detail['Policy']['DefaultVersionId']
                    )
                    
                    user_policies.append({
                        'name': policy['PolicyName'],
                        'arn': policy['PolicyArn'],
                        'document': policy_version['PolicyVersion']['Document']
                    })
                
                user_info['policies'] = user_policies
            except Exception as e:
                logger.error(f"{log_prefix}Error getting policies for {user['UserName']}: {str(e)}")

            result['users'].append(user_info)
        
        # 2. 루트 계정 액세스 키 확인
        logger.info(f"{log_prefix}Checking root account access keys")
        try:
            summary = iam_client.get_account_summary()
            result['root_account'] = {
                'access_key_exists': summary['SummaryMap'].get('AccountAccessKeysPresent', 0) > 0,
                'mfa_enabled': summary['SummaryMap'].get('AccountMFAEnabled', 0) > 0
            }
        except Exception as e:
            logger.error(f"{log_prefix}Error checking root account: {str(e)}")
        
        # 3. 비밀번호 정책 확인
        logger.info(f"{log_prefix}Checking password policy")
        try:
            password_policy = iam_client.get_account_password_policy()
            result['password_policy'] = password_policy['PasswordPolicy']
        except iam_client.exceptions.NoSuchEntityException:
            result['password_policy'] = {'exists': False}
        except Exception as e:
            logger.error(f"{log_prefix}Error checking password policy: {str(e)}")
        
        # 4. IAM 역할 및 신뢰 관계 확인
        logger.info(f"{log_prefix}Collecting IAM roles and trust relationships")
        try:
            roles = iam_client.list_roles()
            for role in roles['Roles']:
                role_info = {
                    'name': role['RoleName'],
                    'arn': role['Arn'],
                    'created': role['CreateDate'].strftime('%Y-%m-%d'),
                    'trust_policy': role['AssumeRolePolicyDocument'],
                    'service_linked': role.get('Path', '').startswith('/service-role/'),
                    'policies': []
                }
                
                # 역할에 연결된 정책 확인
                try:
                    attached_policies = iam_client.list_attached_role_policies(RoleName=role['RoleName'])
                    for policy in attached_policies['AttachedPolicies']:
                        policy_detail = iam_client.get_policy(PolicyArn=policy['PolicyArn'])
                        policy_version = iam_client.get_policy_version(
                            PolicyArn=policy['PolicyArn'],
                            VersionId=policy_detail['Policy']['DefaultVersionId']
                        )
                        
                        role_info['policies'].append({
                            'name': policy['PolicyName'],
                            'arn': policy['PolicyArn'],
                            'document': policy_version['PolicyVersion']['Document']
                        })
                except Exception as e:
                    logger.error(f"{log_prefix}Error getting policies for role {role['RoleName']}: {str(e)}")
                
                result['roles'].append(role_info)
        except Exception as e:
            logger.error(f"{log_prefix}Error collecting roles: {str(e)}")
        
        # 5. 고객 관리형 정책 확인
        logger.info(f"{log_prefix}Collecting customer managed policies")
        try:
            policies = iam_client.list_policies(Scope='Local')
            for policy in policies['Policies']:
                policy_info = {
                    'name': policy['PolicyName'],
                    'arn': policy['Arn'],
                    'created': policy['CreateDate'].strftime('%Y-%m-%d'),
                    'attachment_count': policy['AttachmentCount']
                }
                
                # 정책 문서 확인
                try:
                    policy_version = iam_client.get_policy_version(
                        PolicyArn=policy['Arn'],
                        VersionId=policy['DefaultVersionId']
                    )
                    policy_info['document'] = policy_version['PolicyVersion']['Document']
                except Exception as e:
                    logger.error(f"{log_prefix}Error getting policy document for {policy['PolicyName']}: {str(e)}")
                
                result['policies'].append(policy_info)
        except Exception as e:
            logger.error(f"{log_prefix}Error collecting policies: {str(e)}")
        
        logger.info(f"{log_prefix}Successfully collected IAM data")
        return result
    except Exception as e:
        logger.error(f"{log_prefix}Error in get_iam_data: {str(e)}")
        return {'error': str(e)}
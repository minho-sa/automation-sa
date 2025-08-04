from datetime import datetime
from typing import Dict, List, Any
import pytz
import logging
from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.common.resource_model import IAMUser, IAMRole

class IAMCollector(BaseCollector):
    """
    IAM 데이터 수집기
    """
    
    def _init_clients(self) -> None:
        """
        필요한 AWS 클라이언트 초기화
        """
        self.iam_client = self.get_client('iam')
    
    def collect(self, collection_id: str = None) -> Dict[str, Any]:
        """
        IAM 데이터 수집
        
        Args:
            collection_id: 수집 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: 수집된 IAM 데이터
        """
        log_prefix = f"[{collection_id}] " if collection_id else ""
        self.logger.info(f"{log_prefix}IAM 데이터 수집 시작")
        
        # 권한 확인
        if not self._check_permissions(log_prefix):
            return {
                'users': [],
                'roles': [],
                'policies': [],
                'summary': {
                    'total_users': 0,
                    'total_roles': 0,
                    'total_policies': 0,
                    'users_with_console_access': 0,
                    'users_with_mfa': 0
                },
                'error': 'IAM 서비스에 대한 권한이 부족합니다.'
            }
        
        try:
            current_time = datetime.now(pytz.UTC)
            
            # 사용자 수집
            users = self._collect_users(log_prefix)
            
            # 정책 수집 (관리형 정책만)
            policies = self._collect_policies(log_prefix)
            
            # 요약 정보 생성
            summary = self._generate_summary(users, [], policies)
            
            result = {
                'users': users,
                'roles': [],
                'policies': policies,
                'summary': summary
            }
            
            self.logger.info(f"{log_prefix}IAM 데이터 수집 완료 - 사용자: {len(users)}, 정책: {len(policies)}")
            return result
            
        except Exception as e:
            self.logger.error(f"{log_prefix}IAM 데이터 수집 중 오류 발생: {str(e)}")
            return {
                'users': [],
                'roles': [],
                'policies': [],
                'summary': {
                    'total_users': 0,
                    'total_roles': 0,
                    'total_policies': 0,
                    'users_with_console_access': 0,
                    'users_with_mfa': 0
                },
                'error': str(e)
            }
    

    def _collect_users(self, log_prefix: str) -> List[Dict[str, Any]]:
        """IAM 사용자 수집"""
        users = []
        try:
            paginator = self.iam_client.get_paginator('list_users')
            
            for page in paginator.paginate():
                for user_data in page['Users']:
                    try:
                        user = self._process_user(user_data, log_prefix)
                        users.append(user.to_dict())
                    except Exception as e:
                        self.logger.warning(f"{log_prefix}사용자 {user_data.get('UserName', 'Unknown')} 처리 중 오류: {str(e)}")
                        continue
            
            self.logger.info(f"{log_prefix}IAM 사용자 {len(users)}개 수집 완료")
            
        except Exception as e:
            self.logger.error(f"{log_prefix}IAM 사용자 수집 중 오류: {str(e)}")
        
        return users
    

    
    def _collect_policies(self, log_prefix: str) -> List[Dict[str, Any]]:
        """IAM 정책 수집 (관리형 정책만)"""
        policies = []
        try:
            paginator = self.iam_client.get_paginator('list_policies')
            
            for page in paginator.paginate(Scope='Local'):  # 고객 관리형 정책만
                for policy_data in page['Policies']:
                    try:
                        policy_dict = {
                            'id': policy_data['Arn'],
                            'name': policy_data['PolicyName'],
                            'arn': policy_data['Arn'],
                            'path': policy_data['Path'],
                            'create_date': policy_data['CreateDate'].isoformat() if policy_data.get('CreateDate') else '',
                            'update_date': policy_data['UpdateDate'].isoformat() if policy_data.get('UpdateDate') else '',
                            'attachment_count': policy_data.get('AttachmentCount', 0),
                            'permissions_boundary_usage_count': policy_data.get('PermissionsBoundaryUsageCount', 0),
                            'is_attachable': policy_data.get('IsAttachable', False),
                            'description': policy_data.get('Description', ''),
                            'region': self.region,
                            'tags': []
                        }
                        policies.append(policy_dict)
                    except Exception as e:
                        self.logger.warning(f"{log_prefix}정책 {policy_data.get('PolicyName', 'Unknown')} 처리 중 오류: {str(e)}")
                        continue
            
            self.logger.info(f"{log_prefix}IAM 정책 {len(policies)}개 수집 완료")
            
        except Exception as e:
            self.logger.error(f"{log_prefix}IAM 정책 수집 중 오류: {str(e)}")
        
        return policies
    
    def _process_user(self, user_data: Dict[str, Any], log_prefix: str) -> IAMUser:
        """IAM 사용자 데이터 처리"""
        user_name = user_data['UserName']
        
        user = IAMUser(
            id=user_name,
            region=self.region,
            user_name=user_name,
            path=user_data.get('Path', '/'),
            create_date=user_data.get('CreateDate'),
            password_last_used=user_data.get('PasswordLastUsed')
        )
        
        # 추가 정보 수집
        try:
            # 액세스 키 정보
            access_keys = self.iam_client.list_access_keys(UserName=user_name)
            user.access_keys = access_keys.get('AccessKeyMetadata', [])
            user.has_active_access_keys = any(key['Status'] == 'Active' for key in user.access_keys)
            
            # 콘솔 패스워드 확인
            try:
                self.iam_client.get_login_profile(UserName=user_name)
                user.has_console_password = True
            except self.iam_client.exceptions.NoSuchEntityException:
                user.has_console_password = False
            except Exception:
                user.has_console_password = False
            
            # MFA 디바이스 확인
            mfa_devices = self.iam_client.list_mfa_devices(UserName=user_name)
            user.mfa_devices = mfa_devices.get('MFADevices', [])
            
            # 그룹 멤버십
            groups = self.iam_client.get_groups_for_user(UserName=user_name)
            user.groups = [group['GroupName'] for group in groups.get('Groups', [])]
            
            # 연결된 정책
            attached_policies = self.iam_client.list_attached_user_policies(UserName=user_name)
            user.attached_policies = attached_policies.get('AttachedPolicies', [])
            
            # 인라인 정책
            inline_policies = self.iam_client.list_user_policies(UserName=user_name)
            user.inline_policies = [{'PolicyName': name} for name in inline_policies.get('PolicyNames', [])]
            
        except Exception as e:
            self.logger.warning(f"{log_prefix}사용자 {user_name} 추가 정보 수집 중 오류: {str(e)}")
        
        # 추가 계산 정보
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        # 마지막 활동 계산
        last_activity_days = None
        if user.password_last_used:
            if isinstance(user.password_last_used, str):
                try:
                    last_used = datetime.fromisoformat(user.password_last_used.replace('Z', '+00:00'))
                    last_activity_days = (now - last_used).days
                except:
                    pass
            else:
                last_activity_days = (now - user.password_last_used.replace(tzinfo=timezone.utc)).days
        
        # 암호 수명 계산 (생성일부터)
        password_age_days = None
        if user.create_date:
            if isinstance(user.create_date, str):
                try:
                    created = datetime.fromisoformat(user.create_date.replace('Z', '+00:00'))
                    password_age_days = (now - created).days
                except:
                    pass
            else:
                password_age_days = (now - user.create_date.replace(tzinfo=timezone.utc)).days
        
        # 액세스 키 수명 계산 (가장 오래된 키)
        access_key_age_days = None
        if user.access_keys:
            oldest_key_date = None
            for key in user.access_keys:
                key_date = key.get('CreateDate')
                if key_date:
                    if isinstance(key_date, str):
                        try:
                            key_date = datetime.fromisoformat(key_date.replace('Z', '+00:00'))
                        except:
                            continue
                    else:
                        key_date = key_date.replace(tzinfo=timezone.utc)
                    
                    if oldest_key_date is None or key_date < oldest_key_date:
                        oldest_key_date = key_date
            
            if oldest_key_date:
                access_key_age_days = (now - oldest_key_date).days
        
        # 추가 정보를 사용자 객체에 저장
        user.last_activity_days = last_activity_days
        user.password_age_days = password_age_days
        user.access_key_age_days = access_key_age_days
        
        return user
    

    
    def _generate_summary(self, users: List[Dict], roles: List[Dict], policies: List[Dict]) -> Dict[str, Any]:
        """요약 정보 생성"""
        users_with_console_access = sum(1 for user in users if user.get('has_console_password', False))
        users_with_mfa = sum(1 for user in users if user.get('mfa_devices', []))
        
        # 디버깅 로그
        self.logger.info(f"IAM 요약 계산 - 총 사용자: {len(users)}, 콘솔 액세스: {users_with_console_access}, MFA: {users_with_mfa}")
        for user in users:
            console_access = user.get('has_console_password', False)
            mfa_count = len(user.get('mfa_devices', []))
            self.logger.info(f"사용자 {user.get('user_name')}: 콘솔={console_access}, MFA={mfa_count}개")
        
        return {
            'total_users': len(users),
            'total_roles': len(roles),
            'total_policies': len(policies),
            'users_with_console_access': users_with_console_access,
            'users_with_mfa': users_with_mfa
        }
    
    def _check_permissions(self, log_prefix: str) -> bool:
        """IAM 서비스 접근 권한 확인"""
        try:
            self.iam_client.list_users(MaxItems=1)
            self.logger.debug(f"{log_prefix}IAM 권한 확인 성공")
            return True
        except Exception as e:
            error_msg = str(e)
            if 'AccessDenied' in error_msg or 'UnauthorizedOperation' in error_msg:
                self.logger.error(f"{log_prefix}IAM 접근 권한 부족: {error_msg}")
            else:
                self.logger.error(f"{log_prefix}IAM 권한 확인 중 오류: {error_msg}")
            return False
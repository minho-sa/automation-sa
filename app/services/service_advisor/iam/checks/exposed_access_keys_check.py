"""
노출된 액세스 키 검사
"""

import boto3
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.services.service_advisor.common.aws_client import AWSClient

class ExposedAccessKeysCheck:
    """노출된 액세스 키 검사 클래스"""
    
    def __init__(self):
        self.check_id = 'iam-exposed-access-keys'
        
        # 의심스러운 액세스 패턴 정의
        self.suspicious_patterns = {
            'unusual_regions': ['ap-northeast-3', 'eu-north-1', 'me-south-1', 'af-south-1'],
            'high_risk_actions': [
                'iam:CreateUser', 'iam:CreateRole', 'iam:AttachUserPolicy',
                'ec2:RunInstances', 'ec2:CreateSecurityGroup', 'ec2:AuthorizeSecurityGroupIngress',
                's3:PutBucketPolicy', 's3:PutBucketAcl', 's3:DeleteBucket'
            ],
            'max_failed_attempts': 10,
            'unusual_user_agents': ['curl', 'wget', 'python-requests', 'boto3']
        }
    
    def run(self, role_arn: str = None) -> Dict[str, Any]:
        """노출된 액세스 키 검사 실행"""
        try:
            aws_client = AWSClient()
            
            # 1. IAM 사용자 및 액세스 키 정보 수집
            iam_client = aws_client.get_client('iam', 'us-east-1', role_arn)
            users_with_keys = self._get_users_with_access_keys(iam_client)
            
            # 2. CloudTrail 로그 분석 (최근 7일)
            suspicious_activities = self._analyze_cloudtrail_logs(aws_client, role_arn, users_with_keys)
            
            # 3. 액세스 키 사용 패턴 분석
            risky_keys = self._analyze_access_key_patterns(suspicious_activities)
            
            # 결과 분석
            if not risky_keys:
                return {
                    'status': 'ok',
                    'message': '의심스러운 액세스 키 사용 패턴이 발견되지 않았습니다.',
                    'resources': [],
                    'recommendations': []
                }
            
            # 위험도별 분류
            high_risk_keys = [key for key in risky_keys if key['risk_level'] == 'high']
            medium_risk_keys = [key for key in risky_keys if key['risk_level'] == 'medium']
            
            if high_risk_keys:
                status = 'error'
                message = f"높은 위험도의 노출 가능성이 있는 액세스 키 {len(high_risk_keys)}개가 발견되었습니다."
            elif medium_risk_keys:
                status = 'warning'
                message = f"중간 위험도의 의심스러운 액세스 키 사용 패턴 {len(medium_risk_keys)}개가 발견되었습니다."
            else:
                status = 'warning'
                message = f"의심스러운 액세스 키 사용 패턴 {len(risky_keys)}개가 발견되었습니다."
            
            recommendations = [
                "의심스러운 액세스 키는 비활성화하고 새로운 키로 교체하세요.",
                "CloudTrail 로그를 정기적으로 모니터링하여 비정상적인 활동을 감지하세요.",
                "액세스 키 대신 IAM 역할과 임시 자격 증명을 사용하는 것을 권장합니다.",
                "GitHub, GitLab 등 공개 저장소에 액세스 키가 노출되지 않았는지 확인하세요.",
                "의심스러운 활동이 감지되면 즉시 보안 팀에 알리고 대응 절차를 수행하세요."
            ]
            
            return {
                'status': status,
                'message': message,
                'resources': risky_keys,
                'recommendations': recommendations
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'노출된 액세스 키 검사 중 오류가 발생했습니다: {str(e)}',
                'resources': [],
                'recommendations': []
            }
    
    def _get_users_with_access_keys(self, iam_client) -> Dict[str, Dict]:
        """액세스 키를 가진 IAM 사용자 정보 수집"""
        users_with_keys = {}
        
        try:
            # IAM 사용자 목록 가져오기
            paginator = iam_client.get_paginator('list_users')
            
            for page in paginator.paginate():
                for user in page['Users']:
                    user_name = user['UserName']
                    
                    # 사용자의 액세스 키 목록 가져오기
                    try:
                        keys_response = iam_client.list_access_keys(UserName=user_name)
                        access_keys = keys_response['AccessKeyMetadata']
                        
                        if access_keys:
                            users_with_keys[user_name] = {
                                'user_info': user,
                                'access_keys': access_keys
                            }
                    except Exception as e:
                        print(f"Error getting access keys for user {user_name}: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error listing IAM users: {str(e)}")
        
        return users_with_keys
    
    def _analyze_cloudtrail_logs(self, aws_client, role_arn: str, users_with_keys: Dict) -> List[Dict]:
        """CloudTrail 로그 분석"""
        suspicious_activities = []
        
        try:
            # CloudTrail 클라이언트 생성 (us-east-1에서 글로벌 이벤트 조회)
            cloudtrail_client = aws_client.get_client('cloudtrail', 'us-east-1', role_arn)
            
            # 최근 7일간의 이벤트 조회
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            # 모든 사용자의 액세스 키에 대해 이벤트 조회
            for user_name, user_data in users_with_keys.items():
                for access_key in user_data['access_keys']:
                    access_key_id = access_key['AccessKeyId']
                    
                    try:
                        # CloudTrail 이벤트 조회
                        events = self._get_cloudtrail_events(
                            cloudtrail_client, access_key_id, start_time, end_time
                        )
                        
                        # 의심스러운 패턴 분석
                        suspicious_events = self._analyze_events_for_suspicious_patterns(
                            events, user_name, access_key_id
                        )
                        
                        if suspicious_events:
                            suspicious_activities.extend(suspicious_events)
                            
                    except Exception as e:
                        print(f"Error analyzing CloudTrail for key {access_key_id}: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error accessing CloudTrail: {str(e)}")
        
        return suspicious_activities
    
    def _get_cloudtrail_events(self, cloudtrail_client, access_key_id: str, start_time, end_time) -> List[Dict]:
        """특정 액세스 키의 CloudTrail 이벤트 조회"""
        events = []
        
        try:
            paginator = cloudtrail_client.get_paginator('lookup_events')
            
            # 액세스 키 ID로 이벤트 필터링
            page_iterator = paginator.paginate(
                LookupAttributes=[
                    {
                        'AttributeKey': 'AccessKeyId',
                        'AttributeValue': access_key_id
                    }
                ],
                StartTime=start_time,
                EndTime=end_time
            )
            
            for page in page_iterator:
                events.extend(page.get('Events', []))
                
        except Exception as e:
            print(f"Error getting CloudTrail events: {str(e)}")
        
        return events
    
    def _analyze_events_for_suspicious_patterns(self, events: List[Dict], user_name: str, access_key_id: str) -> List[Dict]:
        """이벤트에서 의심스러운 패턴 분석"""
        suspicious_events = []
        
        # 패턴 분석을 위한 데이터 수집
        regions = set()
        source_ips = set()
        user_agents = set()
        failed_attempts = 0
        high_risk_actions = []
        
        for event in events:
            # 지역 정보
            aws_region = event.get('AwsRegion', '')
            if aws_region:
                regions.add(aws_region)
            
            # 소스 IP
            source_ip = event.get('SourceIPAddress', '')
            if source_ip:
                source_ips.add(source_ip)
            
            # User Agent (CloudTrail 이벤트에서 추출)
            event_detail = event.get('CloudTrailEvent', '{}')
            try:
                detail_json = json.loads(event_detail)
                user_agent = detail_json.get('userAgent', '')
                if user_agent:
                    user_agents.add(user_agent)
            except:
                pass
            
            # 실패한 시도
            error_code = event.get('ErrorCode')
            if error_code:
                failed_attempts += 1
            
            # 고위험 액션
            event_name = event.get('EventName', '')
            if event_name in self.suspicious_patterns['high_risk_actions']:
                high_risk_actions.append({
                    'event_name': event_name,
                    'event_time': event.get('EventTime'),
                    'source_ip': source_ip,
                    'aws_region': aws_region
                })
        
        # 의심스러운 패턴 감지
        risk_factors = []
        risk_level = 'low'
        
        # 1. 비정상적인 지역에서의 접근
        unusual_regions = regions.intersection(set(self.suspicious_patterns['unusual_regions']))
        if unusual_regions:
            risk_factors.append(f"비정상적인 지역에서 접근: {', '.join(unusual_regions)}")
            risk_level = 'medium'
        
        # 2. 과도한 실패 시도
        if failed_attempts > self.suspicious_patterns['max_failed_attempts']:
            risk_factors.append(f"과도한 실패 시도: {failed_attempts}회")
            risk_level = 'high'
        
        # 3. 고위험 액션 수행
        if high_risk_actions:
            risk_factors.append(f"고위험 액션 수행: {len(high_risk_actions)}회")
            risk_level = 'high'
        
        # 4. 의심스러운 User Agent
        suspicious_agents = []
        for agent in user_agents:
            for suspicious_agent in self.suspicious_patterns['unusual_user_agents']:
                if suspicious_agent.lower() in agent.lower():
                    suspicious_agents.append(agent)
        
        if suspicious_agents:
            risk_factors.append(f"의심스러운 User Agent: {', '.join(set(suspicious_agents))}")
            risk_level = 'medium'
        
        # 5. 다수의 서로 다른 IP에서 접근
        if len(source_ips) > 5:
            risk_factors.append(f"다수의 IP에서 접근: {len(source_ips)}개")
            risk_level = 'medium'
        
        # 의심스러운 패턴이 발견된 경우
        if risk_factors:
            suspicious_events.append({
                'user_name': user_name,
                'access_key_id': access_key_id,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'event_count': len(events),
                'unique_regions': len(regions),
                'unique_ips': len(source_ips),
                'failed_attempts': failed_attempts,
                'high_risk_actions': len(high_risk_actions)
            })
        
        return suspicious_events
    
    def _analyze_access_key_patterns(self, suspicious_activities: List[Dict]) -> List[Dict]:
        """액세스 키 패턴 분석 및 위험도 평가"""
        risky_keys = []
        
        for activity in suspicious_activities:
            # 위험도 점수 계산
            risk_score = self._calculate_risk_score(activity)
            
            # 상태 및 조치 사항 결정
            if risk_score >= 80:
                status = 'fail'
                status_text = '높은 위험'
                advice = f"액세스 키 {activity['access_key_id']}는 즉시 비활성화하고 보안 검토를 수행하세요."
            elif risk_score >= 50:
                status = 'warning'
                status_text = '중간 위험'
                advice = f"액세스 키 {activity['access_key_id']}의 사용 패턴을 면밀히 모니터링하세요."
            else:
                status = 'warning'
                status_text = '낮은 위험'
                advice = f"액세스 키 {activity['access_key_id']}에 대한 추가 모니터링을 권장합니다."
            
            risky_keys.append({
                'user_name': activity['user_name'],
                'access_key_id': activity['access_key_id'],
                'risk_level': activity['risk_level'],
                'risk_score': risk_score,
                'risk_factors': activity['risk_factors'],
                'event_count': activity['event_count'],
                'unique_regions': activity['unique_regions'],
                'unique_ips': activity['unique_ips'],
                'failed_attempts': activity['failed_attempts'],
                'high_risk_actions': activity['high_risk_actions'],
                'status': status,
                'status_text': status_text,
                'advice': advice
            })
        
        return risky_keys
    
    def _calculate_risk_score(self, activity: Dict) -> int:
        """위험도 점수 계산"""
        score = 0
        
        # 기본 점수
        if activity['risk_level'] == 'high':
            score += 50
        elif activity['risk_level'] == 'medium':
            score += 30
        else:
            score += 10
        
        # 실패 시도 점수
        if activity['failed_attempts'] > 20:
            score += 30
        elif activity['failed_attempts'] > 10:
            score += 20
        elif activity['failed_attempts'] > 5:
            score += 10
        
        # 고위험 액션 점수
        if activity['high_risk_actions'] > 5:
            score += 25
        elif activity['high_risk_actions'] > 0:
            score += 15
        
        # 다수 IP 접근 점수
        if activity['unique_ips'] > 10:
            score += 20
        elif activity['unique_ips'] > 5:
            score += 10
        
        # 다수 지역 접근 점수
        if activity['unique_regions'] > 3:
            score += 15
        elif activity['unique_regions'] > 1:
            score += 5
        
        return min(score, 100)  # 최대 100점

def run(role_arn: str = None) -> Dict[str, Any]:
    """검사 실행 함수"""
    check = ExposedAccessKeysCheck()
    return check.run(role_arn)
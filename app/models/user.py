from flask_login import UserMixin

class User(UserMixin):
    """사용자 모델 클래스"""
    
    def __init__(self, user_data):
        """
        사용자 모델 초기화
        
        Args:
            user_data: S3에서 가져온 사용자 정보 딕셔너리
        """
        self.id = user_data.get('username')
        self.username = user_data.get('username')
        self.role_arn = user_data.get('role_arn')
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        
    def get_id(self):
        """사용자 ID 반환"""
        return self.id
        
    def get_role_arn(self):
        """사용자의 AWS Role ARN 반환"""
        return self.role_arn
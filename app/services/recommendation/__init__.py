# Import recommendation functions for easy access
from app.services.recommendation.get_ec2_recommendations import get_ec2_recommendations
from app.services.recommendation.get_s3_recommendations import get_s3_recommendations
from app.services.recommendation.get_lambda_recommendations import get_lambda_recommendations
from app.services.recommendation.get_iam_recommendations import get_iam_recommendations
from app.services.recommendation.rds import get_rds_recommendations

# 아직 구현되지 않은 함수들에 대한 임시 구현

def get_cloudwatch_recommendations(*args, **kwargs):
    return []

def get_dynamodb_recommendations(*args, **kwargs):
    return []

def get_ecs_recommendations(*args, **kwargs):
    return []

def get_eks_recommendations(*args, **kwargs):
    return []

def get_sns_recommendations(*args, **kwargs):
    return []

def get_sqs_recommendations(*args, **kwargs):
    return []

def get_apigateway_recommendations(*args, **kwargs):
    return []

def get_elasticache_recommendations(*args, **kwargs):
    return []

def get_route53_recommendations(*args, **kwargs):
    return []
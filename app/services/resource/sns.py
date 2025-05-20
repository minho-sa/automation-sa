from app.services.resource.base_service import create_boto3_client

def get_sns_data(aws_access_key, aws_secret_key, region, collection_id=None, aws_session_token=None):
    """SNS 주제 데이터 수집"""
    try:
        sns_client = create_boto3_client('sns', region, aws_access_key, aws_secret_key, aws_session_token)
        
        response = sns_client.list_topics()
        topics = []
        
        for topic in response['Topics']:
            topic_arn = topic['TopicArn']
            topic_name = topic_arn.split(':')[-1]
            
            # 구독 정보 가져오기
            subscriptions_response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            subscriptions_count = len(subscriptions_response.get('Subscriptions', []))
            
            # 주제 속성 가져오기
            attributes_response = sns_client.get_topic_attributes(TopicArn=topic_arn)
            
            topics.append({
                'name': topic_name,
                'arn': topic_arn,
                'subscriptions': subscriptions_count,
                'effective_delivery_policy': 'DeliveryPolicy' in attributes_response['Attributes']
            })
        
        return {'topics': topics}
    except Exception as e:
        return {'error': str(e)}
from app.services.resource.base_service import create_boto3_client

def get_apigateway_data(aws_access_key, aws_secret_key, region, collection_id=None, aws_session_token=None):
    """API Gateway 데이터 수집"""
    try:
        apigateway_client = create_boto3_client('apigateway', region, aws_access_key, aws_secret_key, aws_session_token)
        
        response = apigateway_client.get_rest_apis()
        apis = []
        
        for api in response['items']:
            # 스테이지 정보 가져오기
            stages_response = apigateway_client.get_stages(restApiId=api['id'])
            
            apis.append({
                'id': api['id'],
                'name': api['name'],
                'description': api.get('description', 'No description'),
                'created_date': api['createdDate'].strftime('%Y-%m-%d'),
                'stages': len(stages_response.get('item', [])),
                'api_key_required': api.get('apiKeyRequired', False)
            })
        
        return {'apis': apis}
    except Exception as e:
        return {'error': str(e)}
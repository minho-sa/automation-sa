from app.services.resource.base_service import create_boto3_client

def get_route53_data(aws_access_key, aws_secret_key, region, collection_id=None, aws_session_token=None):
    """Route 53 호스팅 영역 데이터 수집"""
    try:
        route53_client = create_boto3_client('route53', region, aws_access_key, aws_secret_key, aws_session_token)
        
        # 호스팅 영역 정보 가져오기
        response = route53_client.list_hosted_zones()
        zones = []
        
        for zone in response['HostedZones']:
            zone_id = zone['Id'].split('/')[-1]
            
            # 레코드 세트 정보 가져오기
            records_response = route53_client.list_resource_record_sets(HostedZoneId=zone_id)
            
            zones.append({
                'id': zone_id,
                'name': zone['Name'],
                'records': len(records_response['ResourceRecordSets']),
                'private': zone.get('Config', {}).get('PrivateZone', False)
            })
        
        return {'zones': zones}
    except Exception as e:
        return {'error': str(e)}
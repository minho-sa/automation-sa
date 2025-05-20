from app.services.resource.base_service import create_boto3_client

def get_elasticache_data(aws_access_key, aws_secret_key, region, collection_id=None, aws_session_token=None):
    """ElastiCache 클러스터 데이터 수집"""
    try:
        elasticache_client = create_boto3_client('elasticache', region, aws_access_key, aws_secret_key, aws_session_token)
        
        # 캐시 클러스터 정보 가져오기
        response = elasticache_client.describe_cache_clusters()
        clusters = []
        
        for cluster in response['CacheClusters']:
            clusters.append({
                'id': cluster['CacheClusterId'],
                'engine': cluster['Engine'],
                'status': cluster['CacheClusterStatus'],
                'node_type': cluster['CacheNodeType'],
                'nodes': cluster['NumCacheNodes'],
                'engine_version': cluster['EngineVersion']
            })
        
        return {'clusters': clusters}
    except Exception as e:
        return {'error': str(e)}
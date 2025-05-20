from app.services.resource.base_service import create_boto3_client

def get_ecs_data(aws_access_key, aws_secret_key, region, collection_id=None, aws_session_token=None):
    """ECS 클러스터 데이터 수집"""
    try:
        ecs_client = create_boto3_client('ecs', region, aws_access_key, aws_secret_key, aws_session_token)
        
        # 클러스터 목록 가져오기
        clusters_response = ecs_client.list_clusters()
        clusters = []
        
        for cluster_arn in clusters_response['clusterArns']:
            cluster_details = ecs_client.describe_clusters(clusters=[cluster_arn])['clusters'][0]
            
            # 서비스 목록 가져오기
            services_response = ecs_client.list_services(cluster=cluster_arn)
            services_count = len(services_response.get('serviceArns', []))
            
            # 작업 목록 가져오기
            tasks_response = ecs_client.list_tasks(cluster=cluster_arn)
            tasks_count = len(tasks_response.get('taskArns', []))
            
            clusters.append({
                'name': cluster_details['clusterName'],
                'status': cluster_details['status'],
                'services': services_count,
                'tasks': tasks_count,
                'instances': cluster_details.get('registeredContainerInstancesCount', 0)
            })
        
        return {'clusters': clusters}
    except Exception as e:
        return {'error': str(e)}
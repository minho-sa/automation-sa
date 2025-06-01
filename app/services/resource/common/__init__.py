from app.services.resource.common.base_collector import BaseCollector
from app.services.resource.common.resource_model import (
    ResourceModel, 
    EC2Instance, 
    S3Bucket
)
from app.services.resource.common.data_storage import ResourceDataStorage
from app.services.resource.common.collector_result import (
    create_collection_result,
    create_error_result,
    create_success_result,
    STATUS_SUCCESS,
    STATUS_WARNING,
    STATUS_ERROR
)
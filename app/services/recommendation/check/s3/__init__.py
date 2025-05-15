# Import all S3 check functions for easy access
from app.services.recommendation.check.s3.public_access import check_public_access
from app.services.recommendation.check.s3.versioning import check_versioning
from app.services.recommendation.check.s3.encryption import check_encryption
from app.services.recommendation.check.s3.lifecycle_rules import check_lifecycle_rules
from app.services.recommendation.check.s3.tag_management import check_tag_management
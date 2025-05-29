from app.services.service_advisor.lambda_service.checks import (
    memory_size_check,
    timeout_check,
    runtime_check,
    tag_check,
    provisioned_concurrency_check,
    code_signing_check,
    least_privilege_check
)
from app.services.service_advisor.iam.checks import (
    access_key_rotation,
    password_policy,
    mfa_check,
    inactive_users_check,
    root_account_check,
    policy_analyzer_check,
    credential_report_check,
    service_control_policy_check
)
"""
Optional S3 archival service for incident reports.
"""
import json
import logging
from datetime import datetime
from typing import Optional, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


def get_s3_status() -> Tuple[bool, str]:
    """Returns (configured, status_message)."""
    if not settings.s3_bucket:
        return False, "not_configured"
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        s3 = boto3.client("s3", region_name=settings.aws_region)
        s3.head_bucket(Bucket=settings.s3_bucket)
        return True, "connected"
    except Exception as e:
        error_str = str(e)
        if "NoCredentials" in error_str or "NoCredentialsError" in type(e).__name__:
            return False, "credentials_missing"
        if "403" in error_str:
            return False, "access_denied"
        if "404" in error_str or "NoSuchBucket" in error_str:
            return False, "bucket_not_found"
        return False, f"error: {error_str[:80]}"


def archive_report(investigation_id: str, report_data: dict) -> Optional[str]:
    """Upload a report JSON to S3. Returns the S3 URI on success, None on failure."""
    configured, status = get_s3_status()
    if not configured:
        logger.warning(f"S3 archival skipped: {status}")
        return None

    try:
        import boto3
        s3 = boto3.client("s3", region_name=settings.aws_region)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        key = f"{settings.s3_reports_prefix}{investigation_id}/{timestamp}_report.json"
        s3.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=json.dumps(report_data, indent=2, default=str),
            ContentType="application/json",
            Metadata={
                "investigation-id": investigation_id,
                "generated-at": timestamp,
                "application": "incidentlens-ai",
            },
        )
        uri = f"s3://{settings.s3_bucket}/{key}"
        logger.info(f"Report archived to {uri}")
        return uri
    except Exception as e:
        logger.error(f"S3 archival failed: {e}")
        return None

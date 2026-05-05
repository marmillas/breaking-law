"""
Storage infrastructure for legal platform.

Provides S3-compatible object storage with server-side encryption (SSE),
metadata support, signed URLs, and SHA-256 verification.
"""

import hashlib
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Dict, Any


class Storage:
    """S3-compatible storage adapter supporting MinIO (dev) and AWS S3 (production)."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        region_name: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        sse_enabled: bool = True,
        kms_key_id: Optional[str] = None,
    ):
        """
        Initialize storage with bucket and optional S3-compatible endpoint.

        Args:
            bucket_name: Target S3 bucket.
            endpoint_url: Custom endpoint for MinIO or other S3-compatible stores.
            region_name: AWS region (default us-east-1).
            access_key: Optional AWS access key.
            secret_key: Optional AWS secret key.
            sse_enabled: Enable server-side encryption (SSE-S3 or SSE-KMS).
            kms_key_id: Optional KMS key ID for SSE-KMS.
        """
        self.bucket_name = bucket_name
        self.sse_enabled = sse_enabled
        self.kms_key_id = kms_key_id

        session_kwargs: Dict[str, Any] = {}
        if access_key and secret_key:
            session_kwargs["aws_access_key_id"] = access_key
            session_kwargs["aws_secret_access_key"] = secret_key

        session = boto3.session.Session(**session_kwargs)

        client_kwargs: Dict[str, Any] = {
            "region_name": region_name,
            "config": BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        self.s3_client = session.client("s3", **client_kwargs)

    def _get_encryption_headers(self) -> Dict[str, str]:
        """Build encryption headers for upload operations."""
        headers: Dict[str, str] = {}
        if not self.sse_enabled:
            return headers
        if self.kms_key_id:
            headers["x-amz-server-side-encryption"] = "aws:kms"
            headers["x-amz-server-side-encryption-aws-kms-key-id"] = self.kms_key_id
        else:
            headers["x-amz-server-side-encryption"] = "AES256"
        return headers

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> bool:
        """
        Upload a file-like object to storage.

        Args:
            fileobj: Binary file-like object to upload.
            key: Object key (path) in the bucket.
            metadata: Optional user metadata dict.
            content_type: Optional MIME type.

        Returns:
            True on success, False on failure.
        """
        try:
            extra_args: Dict[str, Any] = {}
            extra_args["ServerSideEncryption"] = (
                "aws:kms" if self.kms_key_id else "AES256"
            ) if self.sse_enabled else None
            if self.kms_key_id:
                extra_args["SSEKMSKeyId"] = self.kms_key_id
            if metadata:
                extra_args["Metadata"] = metadata
            if content_type:
                extra_args["ContentType"] = content_type

            # Remove None values
            extra_args = {k: v for k, v in extra_args.items() if v is not None}

            self.s3_client.upload_fileobj(fileobj, self.bucket_name, key, ExtraArgs=extra_args)
            return True
        except ClientError as exc:
            print(f"Storage upload failed for key {key}: {exc}")
            return False

    def download_fileobj(self, key: str, fileobj: BinaryIO) -> bool:
        """
        Download an object from storage into a file-like object.

        Args:
            key: Object key in the bucket.
            fileobj: Writable binary file-like object.

        Returns:
            True on success, False on failure.
        """
        try:
            self.s3_client.download_fileobj(self.bucket_name, key, fileobj)
            return True
        except ClientError as exc:
            print(f"Storage download failed for key {key}: {exc}")
            return False

    def delete_object(self, key: str) -> bool:
        """
        Delete an object from storage.

        Args:
            key: Object key in the bucket.

        Returns:
            True on success, False on failure.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as exc:
            print(f"Storage delete failed for key {key}: {exc}")
            return False

    def generate_presigned_url(
        self, key: str, expiration: int = 300, operation: str = "get_object"
    ) -> Optional[str]:
        """
        Generate a short-lived signed URL for an object.

        Args:
            key: Object key in the bucket.
            expiration: URL expiry time in seconds (default 5 minutes).
            operation: S3 operation (default get_object).

        Returns:
            Signed URL string or None on failure.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod=operation,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as exc:
            print(f"Failed to generate presigned URL for key {key}: {exc}")
            return None

    @staticmethod
    def calculate_sha256(fileobj: BinaryIO) -> str:
        """
        Calculate SHA-256 hash of a file-like object.

        Args:
            fileobj: Readable binary file-like object.

        Returns:
            Hex-encoded SHA-256 digest.
        """
        fileobj.seek(0)
        hasher = hashlib.sha256()
        while chunk := fileobj.read(8192):
            hasher.update(chunk)
        fileobj.seek(0)
        return hasher.hexdigest()

    def head_object(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for an object without downloading it.

        Args:
            key: Object key in the bucket.

        Returns:
            Dict with metadata or None on failure.
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError as exc:
            print(f"Head object failed for key {key}: {exc}")
            return None

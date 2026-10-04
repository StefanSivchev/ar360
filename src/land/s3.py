"""S3 helpers for the landing zone: list a prefix, delete a prefix."""

# S3 accepts at most 1,000 keys per delete request.
MAX_DELETE = 1000


def list_objects(s3, bucket: str, prefix: str) -> dict[str, int]:
    """Key -> size in bytes for every object under prefix."""
    found: dict[str, int] = {}
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
    for page in pages:
        for obj in page.get("Contents", []):
            found[obj["Key"]] = obj["Size"]
    return found


def delete_prefix(s3, bucket: str, prefix: str) -> int:
    """Delete every object under prefix; return how many there were."""
    if not prefix.endswith("/"):
        raise ValueError(f"prefix must end with '/': {prefix!r}")
    keys = list(list_objects(s3, bucket, prefix))
    for i in range(0, len(keys), MAX_DELETE):
        batch = [{"Key": k} for k in keys[i : i + MAX_DELETE]]
        resp = s3.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
        if resp.get("Errors"):
            raise RuntimeError(f"delete failed under {prefix}: {resp['Errors'][0]}")
    return len(keys)

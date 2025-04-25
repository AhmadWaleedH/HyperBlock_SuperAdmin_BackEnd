import boto3
import uuid
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException, status
from app.config import settings

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.base_url = settings.S3_BASE_URL

    async def upload_file(self, file: UploadFile, folder: str = "user-cards") -> str:
        """
        Upload a file to S3 and return the URL
        """
        # Generate a unique file name
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{folder}/{str(uuid.uuid4())}.{file_extension}"
        
        try:
            # Read file content
            file_content = await file.read()
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=unique_filename,
                Body=file_content,
                ContentType=file.content_type
            )
            
            # Return the URL of the uploaded file
            return f"{self.base_url}/{unique_filename}"
            
        except ClientError as e:
            print(f"S3 upload error: {str(e)}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to S3: {str(e)}"
            )
        finally:
            # Reset file pointer for potential future reads
            await file.seek(0)
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from S3
        """
        if not file_url or not file_url.startswith(self.base_url):
            return False
            
        # Extract the key from the URL
        key = file_url.replace(self.base_url + "/", "")
        
        try:
            # Delete the file from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False
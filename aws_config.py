import boto3
import os
from botocore.exceptions import ClientError

class AWSConfig:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.rds_client = boto3.client('rds')
        self.ses_client = boto3.client('ses')
        
        # S3 bucket name
        self.s3_bucket = os.environ.get('S3_BUCKET', 'library-static-files')
        
    def upload_to_s3(self, file_path, object_name=None):
        """S3'e dosya yükle"""
        if object_name is None:
            object_name = file_path
            
        try:
            self.s3_client.upload_file(file_path, self.s3_bucket, object_name)
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{object_name}"
        except ClientError as e:
            print(f"S3 upload error: {e}")
            return None
    
    def get_rds_endpoint(self):
        """RDS endpoint'ini al"""
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier='library-db'
            )
            return response['DBInstances'][0]['Endpoint']['Address']
        except ClientError as e:
            print(f"RDS error: {e}")
            return None
    
    def send_email_ses(self, to_email, subject, body):
        """SES ile email gönder"""
        try:
            response = self.ses_client.send_email(
                Source='noreply@yourdomain.com',
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body}}
                }
            )
            return response['MessageId']
        except ClientError as e:
            print(f"SES error: {e}")
            return None

# Global instance
aws_config = AWSConfig() 
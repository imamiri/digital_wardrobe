import boto3
import json
import logging
from botocore.exceptions import ClientError

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_image_labels(rekognition, image_bytes):
    """
    Detect labels in an image using Amazon Rekognition.
    
    Args:
        rekognition (boto3.client): Rekognition client.
        image_bytes (bytes): Image data in bytes.
        
    Returns:
        list: List of top labels with confidence scores greater than 90%.
    """
    try:
        # Detect labels in the image
        labels = rekognition.detect_labels(Image={'Bytes': image_bytes}, MaxLabels=3)
        logger.info(labels)
        # Extract the top labels and their confidence levels
        top_labels = []
        for l in labels['Labels']:
            if l['Confidence'] > 90:
                top_labels.append(l['Name'])
                
        return top_labels
    except ClientError as e:
        logger.error(f"Error detecting labels: {e}")
        return []

def store_clothing_data(image_key, item_data):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('wardrobe')
    table.put_item(Item={'image_key': image_key, 'item_data': item_data})
    
def lambda_handler(event, context):
    logger.info("Lambda Handler is invoked!")
    # Set up the Rekognition and S3 clients
    rekognition = boto3.client('rekognition')
    s3 = boto3.resource('s3', region_name='eu-west-2')

    # Specify the S3 bucket and prefix (folder) where the images are stored
    results = []
    bucket_name = 'digital-wardrobe-bucket'
    bucket = s3.Bucket(bucket_name)
    image_keys = []
    for bck_obj in bucket.objects.all():
        image_keys.append(bck_obj.key)
    # Get a list of the 10 most recent images in the S3 bucket
    try:
        # Process each image using Rekognition and collect the results
        for image_key in image_keys:
            # Get the image from S3
            image_response = s3.Bucket(bucket_name).Object(image_key).get()
            image_bytes = image_response['Body'].read()
    
            top_labels = get_image_labels(rekognition, image_bytes=image_bytes)
            
            store_clothing_data(image_key, top_labels)
            
            # Add the results to the list
            results.append({
                'ImageKey': image_key,
                'Labels': top_labels
            })
    except ClientError as e:
        logger.error(e)

    logger.info(results)
    return json.dumps(results, indent=2)

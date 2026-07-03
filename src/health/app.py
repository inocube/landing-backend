import json
 
def lambda_handler(event, context):
    """Health-check endpoint. Zatial ziadna logika."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "status": "ok",
            "service": "inocube-backend",
            "version": "0.1.0"
        }),
    }

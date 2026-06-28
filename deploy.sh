#!/bin/bash
EC2="ec2-user@54.85.25.6"
KEY="$HOME/.ssh/lifts-tracker-key.pem"

echo "Deploying to EC2..."
scp -i "$KEY" web_app.py db.py exercise_mapping.py schema.sql "$EC2":~/app/
scp -i "$KEY" templates/*.html "$EC2":~/app/templates/
ssh -i "$KEY" "$EC2" "sudo systemctl restart lifts-tracker"
echo "Done! http://107.21.171.224:5001"

import argparse
import hashlib

# Set up argument parser
parser = argparse.ArgumentParser(description="Hash a password using MD5.")
parser.add_argument("--password", type=str, required=True, help="Password to hash")

# Parse the command-line arguments
args = parser.parse_args()

# Hash the provided password
hashed_password = hashlib.md5(args.password.encode()).hexdigest()

# Print the hashed password
print(hashed_password)

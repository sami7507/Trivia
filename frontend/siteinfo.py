"""
Public links shown in the footer. Change them here, or override with environment variables /
Streamlit secrets (GITHUB_URL, LINKEDIN_URL). A link left empty is simply not shown.
"""
from api_client import _secret

AUTHOR = "Sami"
EMAIL = "sami757007@gmail.com"
GITHUB_URL = _secret("GITHUB_URL", "https://github.com/sami7507")
LINKEDIN_URL = _secret("LINKEDIN_URL", "https://www.linkedin.com/in/sami7507")

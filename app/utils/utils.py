import re

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    text = text.strip('-')
    return text

def get_username_from_email(email_id: str) -> str:
    """
    Extracts the username from an email ID.

    Args:
        email_id: The full email address (e.g., "john.doe@example.com").

    Returns:
        The username part of the email (e.g., "john.doe") if a valid email
        format is detected, otherwise None.
    """
    if "@" in email_id:
        # Split the email ID by the '@' symbol and take the first part
        username = email_id.split("@")[0]
        return username
    else:
        # If no '@' symbol is found, it's not a valid email format for this extraction
        return ''
# coding: utf-8
'''
'''

import re
email_pattern  =re.compile(r"(?:^|\s)[-a-z0-9_.]+@(?:[-a-z0-9]+\.)+[a-z]{2,6}(?:\s|$)",re.IGNORECASE)    
def email_validator(value):
    if not email_pattern.match(value):
        return "%s不是正确的email"
    
    return None

def null_validator(value):
    if value is None:
        return "%s为空值"
    
    return None
        
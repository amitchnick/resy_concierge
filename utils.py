import logging
import sys

def get_logger(name: str):
    root = logging.getLogger(name=name)
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return root

def extract_time_from_token(token: str):
    """extract time from token that looks like: 
    rgs://resy/2/1843946/2/2022-12-18/2022-12-18/20:15:00/2/Indoor Dining"""
    
    split_token = token.split('/')
    return split_token[-3]
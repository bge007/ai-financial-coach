from enum import Enum


class Direction(str, Enum):
    debit = "debit"
    credit = "credit"


class Category(str, Enum):
    rent = "rent"
    sip_investment = "sip_investment"
    groceries = "groceries"
    emi = "emi"
    travel = "travel"
    utilities = "utilities"
    dining = "dining"
    shopping = "shopping"
    salary = "salary"
    transfer = "transfer"
    insurance = "insurance"
    medical = "medical"
    entertainment = "entertainment"
    education = "education"
    other = "other"

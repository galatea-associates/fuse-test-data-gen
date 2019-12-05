from datetime import datetime, timezone
import sys
sys.path.insert(0, 'tests/')
from utils import shared_tests as shared
from utils import helper_methods as helper


def test_cash_flows():
    # records, domain_obj = helper.set_up_cash_flow_tests()
    records = helper.set_up_cash_flow_tests()
    for record in records:
        shared.attribute_quantity_valid('cash_flow', record, 7)
        account_id_valid(record)
        corporate_action_id_valid(record)
        quantity_valid(record)
        shared.currency_valid(record)
        payment_status_valid(record)
        payment_type_valid(record)
        payment_date_valid(record)


def account_id_valid(record):
    """ account id must match to a row in the accounts database table with
    account type of 'Client' or 'Firm'"""
    account_id = record['account_id']
    account_table = shared.domain_obj.retrieve_records('accounts')
    details_in_database = False
    for account in account_table:
        if account['account_id'] == account_id and \
                account['account_type'] in ['Client', 'Firm']:
            details_in_database = True
            break
    assert details_in_database

def corporate_action_id_valid(record):
    """ corporate_action_id must be a 10 character string """
    account_description = record['corporate_action_id']
    assert shared.is_length(10, account_description)
    assert isinstance(account_description, str)

def quantity_valid(record):
    quantity = record['quantity']
    assert isinstance(quantity, float)
    assert 1 <= quantity <= 10000

def payment_status_valid(record):
    assert record['payment_status'] in ['Actual', 'Contractual']

def payment_type_valid(record):
    assert record['payment_type'] == 'Dividend'

def payment_date_valid(record):
    assert record['payment_date'] == datetime.now(timezone.utc).date()
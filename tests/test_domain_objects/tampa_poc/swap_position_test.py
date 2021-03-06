import sys

import pytest

sys.path.insert(0, 'tests/')
from utils import shared_tests as shared
from utils import helper_methods as helper


@pytest.mark.skip(reason="Object being tested belongs to Tampa PoC and is "
                         "not mentioned in the one-pager")
def test_swap_positions():
    pass  # TODO: implement after variable generation
    """
    records, domain_obj = helper.set_up_swap_position_tests()
    for record in records:
        shared.attribute_quantity_valid('swap_position', record, 10)
        shared.ric_exists(record)
        shared.swap_contract_id_exists(record)
        swap_position_type_valid(record, domain_obj.POSITION_TYPES)
        # knowledge_date_valid(record)
        shared.settlement_position_effective_date_valid(record)
        shared.account_valid(record, domain_obj.ACCOUNT_TYPES)
        shared.long_short_valid(record)
        swap_position_quantity_valid(record)
        shared.purpose_valid(record, domain_obj.PURPOSES)
    """


def swap_position_type_valid(record, position_types):
    position_type = record['position_type']
    assert position_type in position_types


def swap_position_quantity_valid(record):
    quantity = record['td_quantity']
    long_short = record['long_short']
    if (long_short == 'Long'):
        assert 1 <= quantity <= 10000
    else:
        assert -10000 <= quantity <= -1

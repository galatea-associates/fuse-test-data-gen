import os
import sys
from multiprocessing import Lock

import ujson

sys.path.insert(0, 'src/')
from database.sqlite_database import Sqlite_Database
from domainobjectfactories import back_office_position_factory, \
    cash_balance_factory, depot_position_factory, \
    front_office_position_factory, \
    instrument_factory, trade_factory, price_factory, \
    account_factory, settlement_instruction_factory, \
    stock_loan_position_factory, cash_flow_factory


# Helper Methods
def delete_local_database():
    if os.path.exists('dependencies.db'):
        os.remove('dependencies.db')


def create_db():
    return Sqlite_Database()


def create_test_table(database, table_name, attribute_dict):
    database.create_table_from_dict(table_name, attribute_dict)


def drop_test_table(database, table_name):
    database.get_connection().execute("DROP TABLE IF EXISTS " + table_name)


def query_db(table_name, attribute=None):
    db = Sqlite_Database()
    result = db.retrieve(table_name)
    if attribute is not None:
        returning = [row[attribute] for row in result]
        return returning
    else:
        return result


# Generation Methods
def create_back_office_position(amount=1):
    obj = back_office_position_factory.BackOfficePositionFactory(None, None)
    return obj.create(amount, 0)


def create_cash_balance(amount=1):
    obj = cash_balance_factory.CashBalanceFactory(None, None)
    return obj.create(amount, 0)


def create_depot_position(amount=1):
    obj = depot_position_factory.DepotPositionFactory(None, None)
    return obj.create(amount, 0)


def create_front_office_position(amount=1):
    obj = front_office_position_factory.FrontOfficePositionFactory(None, None)
    return obj.create(amount, 0)


def create_instrument(amount=1):
    obj = instrument_factory.InstrumentFactory(None, None)
    return obj.create(amount, 0, Lock())


def create_trade(amount=1):
    obj = trade_factory.TradeFactory(None, None)
    return obj.create(amount, 0)


def create_price(amount=1):
    obj = price_factory.PriceFactory(None, None)
    return obj.create(amount, 0)


def create_settlement_instruction(amount=1):
    obj = \
        settlement_instruction_factory.SettlementInstructionFactory(None, None)
    return obj.create(amount, 0)


def create_stock_loan_position(amount=1):
    obj = stock_loan_position_factory.StockLoanPositionFactory(None, None)
    return obj.create(amount, 0)


def create_account(amount=1):
    obj = account_factory.AccountFactory(None, None)
    return obj.create(amount, 0)


def create_cash_flow(amount=1):
    obj = cash_flow_factory.CashFlowFactory(None, None)
    return obj.create(amount, 0)


# Set-up Methods
def set_up_back_office_position_tests():
    delete_local_database()
    create_instrument(50)
    create_account(50)
    records = create_back_office_position(50)
    domain_obj_factory = back_office_position_factory.\
        BackOfficePositionFactory(None, None)
    return records, domain_obj_factory


def set_up_cash_balance_tests():
    delete_local_database()
    create_account(50)
    domain_obj_factory = cash_balance_factory.CashBalanceFactory(None, None)
    records = create_cash_balance(50)
    return records, domain_obj_factory


def set_up_depot_position_tests():
    delete_local_database()
    create_instrument(50)
    create_account(50)
    records = create_depot_position(50)
    domain_obj_factory = depot_position_factory.DepotPositionFactory(None,
                                                                     None)
    return records, domain_obj_factory


def set_up_front_office_position_tests():
    delete_local_database()
    create_instrument(50)
    create_account(50)
    records = create_front_office_position(50)
    domain_obj_factory = front_office_position_factory.\
        FrontOfficePositionFactory(None, None)
    return records, domain_obj_factory


def set_up_instrument_tests():
    delete_local_database()
    return create_instrument(50)


def set_up_trade_tests():
    delete_local_database()
    create_instrument(50)
    create_account(50)
    return create_trade(50)


def set_up_price_tests():
    delete_local_database()
    create_instrument(50)
    return create_price(50)


def set_up_settlement_instruction_tests():
    delete_local_database()
    create_instrument(50)
    create_account(50)
    records = create_settlement_instruction(50)
    domain_obj_factory = settlement_instruction_factory.\
        SettlementInstructionFactory(None, None)

    return records, domain_obj_factory


def set_up_stock_loan_position_tests():
    delete_local_database()
    create_instrument(50)
    records = create_stock_loan_position(50)
    domain_obj_factory = stock_loan_position_factory.StockLoanPositionFactory(
        None,
        None)
    return records, domain_obj_factory


def set_up_account_tests():
    delete_local_database()
    return create_account(50)


def set_up_cash_flow_tests():
    delete_local_database()
    create_account(50)
    records = create_cash_flow(50)
    domain_obj_factory = cash_flow_factory.CashFlowFactory(None, None)
    return records, domain_obj_factory


# Methods related to Tampa PoC
# def create_cashflow(amount=1):
#     config = get_configuration()
#     cashflow_config = config['domain_objects'][11]
#     obj = cashflow_factory.CashflowFactory(cashflow_config)
#     return obj.create(amount, 0)


# def create_counterparty(amount=1):
#     obj = counterparty_factory.CounterpartyFactory(None, None)
#     return obj.create(amount, 0)


# def create_swap_contract(amount=1):
#     config = get_configuration()
#     swap_contract_config = config['domain_objects'][9]
#     obj =
#     swap_contract_factory.SwapContractFactory(swap_contract_config, None)
#     return obj.create(amount, 0)


# def create_swap_position(amount=1):
#     config = get_configuration()
#     swap_position_config = config['domain_objects'][10]
#     obj =
#     swap_position_factory.SwapPositionFactory(swap_position_config, None)
#     return obj.create(amount, 0)

# def set_up_cashflow_tests():
#     delete_local_database()
#     create_instrument(50)
#     create_counterparty(20)
#     create_swap_contract(20)
#     create_swap_position(40)
#     return create_cashflow(20)


# def set_up_counterparty_tests():
#     return create_counterparty(50)


# def set_up_swap_contract_tests():
#     delete_local_database()
#     create_counterparty(20)
#     records = create_swap_contract(20)
#     domain_obj_factory =
#     swap_contract_factory.SwapContractFactory(None, None)
#     return records, domain_obj_factory


# def set_up_swap_position_tests():
#     create_instrument(50)
#     create_counterparty(20)
#     create_swap_contract(20)
#     records = create_swap_position(50)
#     domain_obj_factory =
#     swap_position_factory.SwapPositionFactory(None, None)
#     return records, domain_obj_factory

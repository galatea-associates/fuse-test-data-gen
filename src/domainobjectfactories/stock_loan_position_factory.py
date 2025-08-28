import random
from datetime import datetime, timezone

from domainobjectfactories.creatable import Creatable


class StockLoanPositionFactory(Creatable):
    """ Class to create stock loan positions. Create method will create
    a set amount of positions. Other creation method included where stock
    loan positions are the only domain object requiring them. """

    COLLATERAL_TYPES = ['Cash', 'Non Cash']
    STOCK_LOAN_POSITION_PURPOSES = ['Borrow', 'Loan']

    def create(self, record_count, start_id, lock=None):
        """ Create a set number of stock loan positions

        Parameters
        ----------
        record_count : int
            Number of stock loan positions to create
        start_id : int
            Starting id to create from
        lock : Lock
            Locks critical section of InstrumentFactory class.
            Defaults to None in all other Factory classes.

        Returns
        -------
        List
            Containing 'record_count' stock loan positions

        """
        records = []
        self.instruments = self.retrieve_records('instruments')

        for i in range(start_id, start_id+record_count):
            records.append(self.create_record(i))
        return records

    def create_record(self, id):
        """ Create a single stock loan position record

        Parameters
        ----------
        id : int
            ID of this creation

        Returns
        -------
        dict
            A single stock loan position object
        """

        instrument = self.get_random_instrument()
        position_type = self.create_position_type()
        knowledge_date = self.create_knowledge_date()
        collateral_type = self.create_collateral_type()
        record = {
                'stock_loan_contract_id': id,
                'ric': instrument['ric'],
                'knowledge_date': knowledge_date,
                'effective_date': self.create_effective_date(0,
                                                             knowledge_date,
                                                             position_type),
                'purpose': self.create_purpose(),
                'td_qty': self.create_random_integer(),
                'sd_qty': self.create_random_integer(),
                'collateral_type': collateral_type,
                'haircut': self.create_haircut(collateral_type),
                'collateral_margin': self.create_collateral_margin(
                                                      collateral_type),
                'rebate_rate': self.create_rebate_rate(collateral_type),
                'borrow_fee': self.create_borrow_fee(collateral_type),
                'termination_date': self.create_termination_date(),
                'account': self.create_account(),
                'is_callable': self.create_random_boolean(),
                'return_type': self.create_return_type(),
                'time_stamp': datetime.now(timezone.utc)
            }

        for key, value in self.create_dummy_field_generator():
            record[key] = value

        return record

    def create_haircut(self, collateral_type):
        """ Create a haircut value based on collateral type

        Parameters
        ----------
        collateral_type : String
            The type of collateral used for the loan

        Returns
        -------
        String
            Either a string of percentage, or the fact it's non cash
        """

        return '2.00%' if collateral_type == 'Non Cash' else None

    def create_collateral_margin(self, collateral_type):
        """ Create the collateral margin

        Parameters
        ----------
        collateral_type : String
            The type of collateral used for the loan

        Returns
        -------
        String
            Either a string of percentage, or the fact it's cash
        """

        return '140.00%' if collateral_type == 'Cash' else None

    def create_collateral_type(self):
        """ Create the type of collateral used

        Returns
        -------
        String
            'Cash' or 'Non Cash'
        """

        return random.choice(self.COLLATERAL_TYPES)

    def create_termination_date(self):
        """ Creates a date for the termination of the loan

        Returns
        -------
        Date
            where end date chosen to exist
        Nothing
            where end date chosen to not exist
        """

        does_exist = random.choice([True, False])
        return None if not does_exist else self.create_knowledge_date()

    def create_rebate_rate(self, collateral_type):
        """ Create the rebate rate of the loan

        Parameters
        ----------
        collateral_type : String
            The type of collateral used for the loan

        Returns
        -------
        String
            Percentage where the collateral type is cash
        """

        return '5.75%' if collateral_type == 'Cash' else None

    def create_borrow_fee(self, collateral_type):
        """ Creates the borrow fee of the loan

        Parameters
        ----------
        collateral_type : String
            The type of collateral used for the loan

        Returns
        -------
        String
            Percentage where the collateral type is noncash
        """

        return '4.00%'if collateral_type == 'Non Cash' else None

    def create_purpose(self):
        """ Creates the purpose of the loan

        Returns
        -------
        String
            Random choice between Borrow or Loan
        """

        return random.choice(self.STOCK_LOAN_POSITION_PURPOSES)

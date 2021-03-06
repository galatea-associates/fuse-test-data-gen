import random
from datetime import datetime, timezone, timedelta

from domainobjectfactories.creatable import Creatable


class BackOfficePositionFactory(Creatable):
    """ Class to create back office positions. Create method will create
    a set amount of positions. Other creation methods included where back
    office positions are the only domain object requiring them. """

    LEDGERS = ['TD', 'SD']
    PURPOSES = ['Outright', 'Obligation']

    def create(self, record_count, start_id, lock=None):
        """ Create a set number of back office positions

        Parameters
        ----------
        record_count : int
            Number of back office positions to create
        start_id : int
            Starting id to create from
        lock : Lock
            Locks critical section of InstrumentFactory class.
            Defaults to None in all other Factory classes.

    factory subclasses
        Returns
        -------
        List
            Containing 'record_count' back office positions
        """

        records = []

        for _ in range(start_id, start_id+record_count):
            records.append(self.__create_record())

        return records

    def __create_record(self):
        """ Create a single back office position

        Returns
        -------
        dict
            A single back office position object
        """

        instrument_id, isin = self.__get_instrument_details()
        account_id, account_type = self.__get_account_details()

        record = {
            'as_of_date': self.__create_as_of_date(),
            'value_date': self.__create_value_date(),
            'ledger': self.__create_ledger(),
            'instrument_id': instrument_id,
            'isin': isin,
            'account_id': account_id,
            'account_type': account_type,
            'quantity': self.__create_quantity(),
            'purpose': self.__create_purpose()
        }

        for key, value in self.create_dummy_field_generator():
            record[key] = value

        return record

    @staticmethod
    def __create_as_of_date():
        """ Return the 'as of date', which must be the current date
        Returns
        -------
        Date
            Date object representing the current date
        """
        return datetime.now(timezone.utc).date()

    @staticmethod
    def __create_value_date():
        """ Return the 'value date', which must be today or in 2 days time
        Returns
        -------
        Date
            Date object representing the current date or the date in 2 days
            time
        """
        today = datetime.now(timezone.utc).date()
        day_after_tomorrow = today + timedelta(days=2)
        return random.choice((today, day_after_tomorrow))

    def __create_ledger(self):
        """ Return the 'ledger' string, which must be of the values specified'
        -------
        String
           The ledger, one of 'TD' or 'SD'
        """
        return random.choice(self.LEDGERS)

    def __get_instrument_details(self):
        """ Return the instrument id and isin of an instrument persisted in the
        local database.

        Returns
        -------
        String
            instrument id of instrument from local database
        String
            isin of instrument from local database
        """
        instrument = self.get_random_instrument()
        instrument_id = instrument['instrument_id']
        isin = instrument['isin']
        return instrument_id, isin

    def __get_account_details(self):
        """ Return the account id and account type of an account persisted in
        the database where the type is one of 'Firm', 'Client' or
        'Counterparty'

        Returns
        -------
        String
            account id of account from database
        String
            account type of account from database, must be one of 'Firm',
            'Client' or 'Counterparty'
        """
        account = self.get_random_record_with_valid_attribute(
            'accounts', 'account_type', ['Firm', 'Client', 'Counterparty']
        )
        account_id = account['account_id']
        account_type = account['account_type']
        return account_id, account_type

    def __create_quantity(self):
        """ Return back office position quantity, being a positive or
        negative integer with absolute value not greater than 10000
        Returns
        -------
        int
            positive or negative integer with magnitude <= 10000
        """
        return self.create_random_integer(
            negative=random.choice(self.TRUE_FALSE)
        )

    def __create_purpose(self):
        """ Create a purpose for a back office position

        Returns
        -------
        String
            Back office position purposes are 'outright' or 'obligation''
        """

        return random.choice(self.PURPOSES)

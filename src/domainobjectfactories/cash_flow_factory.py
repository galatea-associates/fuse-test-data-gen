from datetime import datetime, timezone
import random

from domainobjectfactories.creatable import Creatable


class CashFlowFactory(Creatable):
    """ Class to create cash flows. Create method will create
        a set amount of cash flows."""
    PAYMENT_STATUSES = ['Actual', 'Contractual']

    def create(self, record_count, start_id, lock=None):
        """ Create a set number of cash flows

        Parameters
        ----------
        record_count : int
            Number of cash flows to create
        start_id : int
            Starting id to create from
        lock : Lock
            Locks critical section of InstrumentFactory class.
            Defaults to None in all other Factory classes.

        Returns
        -------
        List
            Containing 'record_count' cash flows
        """

        records = []

        for _ in range(start_id, start_id+record_count):
            records.append(self.__create_record())

        return records

    def __create_record(self):
        """ Create a single cash flow

        Returns
        -------
        dict
            A single cash flow object
        """

        record = {
            'account_id': self.__get_account_id(),
            'corporate_action_id': self.__create_corporate_action_id(),
            'quantity': self.__create_quantity(),
            'currency': self.create_currency(),
            'payment_status': self.__create_payment_status(),
            'payment_type': self.__create_payment_type(),
            'payment_date': self.__create_payment_date()
        }

        for key, value in self.create_dummy_field_generator():
            record[key] = value

        return record

    def __get_account_id(self):
        """ Return a account id from an account persisted in the database where
        account type is 'Client' or 'Firm'

        Returns
        -------
        String
            account id from the local database
        """
        account = self.get_random_record_with_valid_attribute(
            'accounts', 'account_type', ['Client', 'Firm']
        )
        account_id = account['account_id']
        return account_id

    def __create_corporate_action_id(self):
        """ Return corporate action id dummy string

        Returns
        -------
        String
            randomly generated 10 character dummy string
        """
        return self.create_random_string(10)

    def __create_quantity(self):
        """ Return quantity of cash in this cashflow
            Returns
            -------
            float
                random number between 1 and 10000 to 2 dp
            """

        return self.create_random_decimal()

    def __create_payment_status(self):
        """ Return the payment status
            Returns
            -------
            String
                payment status, must be one of 'Contractual' or 'Actual'
            """
        return random.choice(self.PAYMENT_STATUSES)

    @staticmethod
    def __create_payment_type():
        """ Return the payment type.  Currently all cash flows represent
         dividend payments, so the value returned will always be 'Dividend'
        Returns
        -------
        String
            'Dividend'
        """

        return 'Dividend'

    @staticmethod
    def __create_payment_date():
        """ Return the payment date, which currently will always be the
        current date
        Returns
        -------
        Date
            Date object representing the current date
        """
        return datetime.now(timezone.utc).date()

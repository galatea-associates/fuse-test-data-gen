import random
import string
from datetime import datetime, timezone

import pandas as pd

from domainobjectfactories.creatable import Creatable


class SwapPositionFactory(Creatable):
    """ Class to create swap positions. Create method will create a set
    amount of swap positions. Other creation methods are included where swap
    positions are the only domain object requiring them.

    Process of creating swap positions dependent on swap contracts, for each
    of these positions, choose a random number of instruments from those
    created prior, then for each position type (start of day, intraday,
    end of day), create a record for every date from the user specified
    start-date until today's date.
    """

    PURPOSES = ['Outright']
    POSITION_TYPES = ['S', 'I', 'E']

    def create(self, record_count, start_id, lock=None):
        """ Create a set number of swap positions

        Parameters
        ----------
        record_count : int
            Number of swap positions to create
        start_id : int
            Starting id to create from

        Returns
        -------
        List
            Containing 'record_count' swap positions
        """

        self.all_instruments = self.retrieve_records('instruments')

        start_date = datetime.strptime(self.get_start_date(), '%Y%m%d')
        date_range = pd.date_range(
            start_date, datetime.now(timezone.utc).date(), freq='D'
        )
        swap_contract_batch =\
            self.retrieve_batch_records('swap_contracts',
                                        record_count, start_id)

        records = [self.create_record(swap_contract, instrument,
                                      position_type, date)
                   for swap_contract in swap_contract_batch
                   for instrument in self.get_random_instruments()
                   for position_type in self.POSITION_TYPES
                   for date in date_range]

        self.persist_records('swap_positions')
        return records

    def create_record(self, swap_contract, instrument, position_type, date):
        """ Create a single swap position

        Parameters
        ----------
        swap_contract : dict
            Swap contract domain object record

        instrument : dict
            Instrument domain object record

        position_type : string
            One of 'S', 'I', or 'E'

        date : datetime
            Randomly selected date that falls between the user-specified start
            date and the current date

        Returns
        -------
        dict
            A single swap position object
        """

        long_short = self.create_long_short()
        purpose = self.create_purpose()
        quantity = self.create_random_integer(
                        negative=long_short.upper() == "SHORT"
                    )
        current_date = datetime.strftime(date, '%Y-%m-%d')

        if position_type == 'E':
            self.persist_record(
                [str(swap_contract['id']),
                 instrument['ric'],
                 position_type,
                 str(current_date),
                 str(long_short)]
            )

        record = {
            'ric': instrument['ric'],
            'swap_contract_id': swap_contract['id'],
            'position_type': position_type,
            'knowledge_date': current_date,
            'effective_date': current_date,
            'account': self.create_account(),
            'long_short': long_short,
            'td_quantity': quantity,
            'purpose': purpose,
            'time_stamp': datetime.now(timezone.utc)
        }

        for key, value in self.create_dummy_field_generator():
            record[key] = value

        return record

    def get_random_instruments(self):
        """ Retrieves a random batch of instruments

        Returns
        -------
        SQLite3 Row
            Random number of instruments retrieved from the database
        """

        ins_count = self.get_number_of_instruments()
        return random.sample(self.all_instruments, ins_count)

    def get_number_of_instruments(self):
        """ Return a random number between the user-specified limits for the
        minimum and maximum amount of instruments per swap

        Returns
        -------
        int
            Random number between the user-specified limits for the minimum
            and maximum amount of instruments per swap
        """

        custom_args = self.get_custom_args()
        ins_per_swap_range = custom_args['ins_per_swap']
        min_ins = int(ins_per_swap_range['min'])
        max_ins = int(ins_per_swap_range['max'])
        return random.randint(min_ins, max_ins)

    def get_start_date(self):
        """ Get the user-specified start date

        Returns
        -------
        String
            String format of the user-specified start date for creation
        """

        custom_args = self.get_custom_args()
        return custom_args['start_date']

    def create_account(self):
        """ Create an account identifier

        Returns
        -------
            Random account type, appended with 4 random digits
        """

        account_type = random.choice(self.ACCOUNT_TYPES)
        random_string = ''.join(random.choices(string.digits, k=4))
        return ''.join([account_type, random_string])

    def create_long_short(self):
        """ Creates a long or short flag randomly

        Returns
        -------
        String
            Random choice between 'Long' or 'Short'
        """

        return random.choice(self.LONG_SHORT)

    def create_purpose(self):
        """ Create swap positions purpose

        Returns
        -------
        String
            Always returns 'outright'
        """

        return random.choice(self.PURPOSES)

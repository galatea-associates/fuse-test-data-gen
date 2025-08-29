import random
import uuid
from datetime import datetime, timedelta, timezone

from domainobjectfactories.creatable import Creatable


class SwapContractFactory(Creatable):
    """ Class to create swap contracts. Create method will create a set
    of swap contracts. Other creation methods are included where swap
    contracts are the only domain object requiring them.

    Process of creating swap contracts is dependent on counterparties, for
    each of these, randomly select a number of swaps between the user-defined
    range, and create a record for each swap.
    """

    SWAP_TYPES = ['Equity', 'Portfolio']
    REFERENCE_RATES = ['LIBOR']

    def create(self, record_count, start_id, lock=None):
        """ Create a set number of swap contracts

        Parameters
        ----------
        record_count : int
            Number of swap contracts to create
        start_id : int
            Starting id to create from

        Returns
        -------
        List
            Containing 'record_count' swap contract
        """

        counterparties =\
            self.retrieve_batch_records('counterparties',
                                        record_count, start_id)

        records = [self.create_record(counterparty['id'])
                   for counterparty in counterparties
                   for _ in range(0, self.get_number_of_swaps())]

        self.persist_records("swap_contracts")
        return records

    def create_record(self, counterparty):
        """ Create a single swap contract

        Parameters
        ----------
        Counterparty : dict
            Dictionary containing a partial record of a counterparty, only
            contains the information necessary to create swap contracts

        Returns
        -------
        dict
            A single swap contract object
        """

        status = self.create_status()
        start_date = self.create_random_date()
        contract_id = str(uuid.uuid1())
        self.persist_record([contract_id])

        record = {
            'counterparty_id': counterparty,
            'swap_contract_id': contract_id,
            'swap_mnemonic': self.create_random_string(10),
            'is_short_mtm_financed': self.create_random_boolean(),
            'accounting_area': self.create_random_string(10),
            'status': status,
            'start_date': start_date,
            'end_date': self.create_swap_end_date(
                                    start_date=start_date,
                                    status=status),
            'swap_type': self.create_swap_type(),
            'reference_rate': self.create_reference_rate(),
            'time_stamp': datetime.now(timezone.utc)
        }

        for key, value in self.create_dummy_field_generator():
            record[key] = value

        return record

    def get_number_of_swaps(self):
        """ Randomly calculate a value between the user-provided minimums
        and maximums.

        Returns
        -------
        int
            The number of swaps
        """

        custom_args = self.get_custom_args()
        swaps_per_counterparty = custom_args['swap_per_counterparty']
        swap_min = int(swaps_per_counterparty['min'])
        swap_max = int(swaps_per_counterparty['max'])
        return random.randint(swap_min, swap_max)

    def create_swap_end_date(self, years_to_add=5,
                             start_date=None, status=None):
        """ Create the end date of the swap

        Parameters
        ----------
        years_to_add : int
            Number of years to add to the start date if contract live
        start_date : Date
            Date from which swap contract commenced
        Status : String
            'Live' or 'Dead' - randomly created beforehand

        Returns
        -------
            String
                If the swap contract is live
            Date
                Where the swap contract is dead, adds specified number of
                years
        """

        return None if status == 'Live' else start_date +\
                       timedelta(days=365 * years_to_add)

    def create_swap_type(self):
        """ Create the type of swap

        Returns
        -------
        String
            Random choice between 'Equity' and 'Portfolio'

        """

        return random.choice(self.SWAP_TYPES)

    def create_reference_rate(self):
        """ Create the reference rate

        Returns
        -------
        String
            Randomly chosen reference rate
        """

        return random.choice(self.REFERENCE_RATES)

    def create_status(self):
        """ Create the current status of the swap

        Returns
        -------
        String
            Random choice between 'Live' and 'Dead'
        """

        return random.choice(['Live', 'Dead'])
